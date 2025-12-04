from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Literal

import AppKit
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    AXValueGetType,
    AXValueGetValue,
    kAXChildrenAttribute,
    kAXIdentifierAttribute,
    kAXListRole,
    kAXPositionAttribute,
    kAXPressAction,
    kAXRaiseAction,
    kAXRoleAttribute,
    kAXSizeAttribute,
    kAXStaticTextRole,
    kAXTextAreaRole,
    kAXTitleAttribute,
    kAXValueAttribute,
    kAXValueCGPointType,
    kAXValueCGSizeType,
)
from PIL import ImageGrab
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)

from .logging_config import logger


def ax_get(element, attribute):
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if err != 0:
        return None
    return value


def dfs(element, predicate: Callable[[Any, Any, Any, Any], bool]):
    if element is None:
        return None

    role = ax_get(element, kAXRoleAttribute)
    title = ax_get(element, kAXTitleAttribute)
    identifier = ax_get(element, kAXIdentifierAttribute)

    if predicate(element, role, title, identifier):
        return element

    children = ax_get(element, kAXChildrenAttribute) or []
    for child in children:
        found = dfs(child, predicate)
        if found is not None:
            return found
    return None


def get_wechat_ax_app() -> Any:
    """
    Get the AX UI element representing the WeChat application and bring
    it to the foreground.
    """
    bundle_id = "com.tencent.xinWeChat"
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        bundle_id
    )
    if not apps:
        raise RuntimeError("WeChat is not running")

    app = apps[0]
    app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
    logger.info(
        "Activated WeChat (bundle_id=%s, pid=%s)", bundle_id, app.processIdentifier()
    )
    return AXUIElementCreateApplication(app.processIdentifier())


def collect_chat_elements(ax_app) -> dict[str, Any]:
    """
    Collect chat elements from the left session list keyed by display name.
    """
    results: dict[str, Any] = {}

    def walk(element):
        role = ax_get(element, kAXRoleAttribute)
        identifier = ax_get(element, kAXIdentifierAttribute)
        if isinstance(role, str) and role == kAXStaticTextRole:
            if isinstance(identifier, str) and identifier.startswith("session_item_"):
                chat_name = identifier[len("session_item_") :]
                if chat_name:
                    results[chat_name] = element

        children = ax_get(element, kAXChildrenAttribute) or []
        for child in children:
            walk(child)

    walk(ax_app)
    logger.info("Collected %d chat elements from session list", len(results))
    return results


def find_chat_element_by_name(ax_app, contact_name: str):
    """
    Find a chat element whose name matches the given contact name exactly
    (case-sensitive and case-insensitive match are both attempted).
    """
    chat_elements = collect_chat_elements(ax_app)
    if contact_name in chat_elements:
        return chat_elements[contact_name]

    lowered = {name.lower(): el for name, el in chat_elements.items()}
    match = lowered.get(contact_name.lower())
    if match is not None:
        return match
    return None


def send_key_with_modifiers(keycode: int, flags: int):
    event_down = CGEventCreateKeyboardEvent(None, keycode, True)
    CGEventSetFlags(event_down, flags)
    event_up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(event_up, flags)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


def find_search_field(ax_app):
    def is_search(el, role, title, identifier):
        return role == kAXTextAreaRole and title == "Search"

    search = dfs(ax_app, is_search)
    if search is None:
        raise RuntimeError(
            "Could not find WeChat search text field via Accessibility API"
        )
    return search


def focus_and_type_search(ax_app, text: str):
    """
    Focus the WeChat sidebar search field and type the given text using
    Command+A and Command+V, similar to search_contacts.py.
    """
    search = find_search_field(ax_app)

    AXUIElementPerformAction(search, kAXRaiseAction)

    # Clear any existing value via AX (best effort).
    AXUIElementCopyAttributeValue(search, kAXValueAttribute, None)

    pb = AppKit.NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, AppKit.NSPasteboardTypeString)

    time.sleep(0.1)

    keycode_a = 0  # US keyboard 'A'
    keycode_v = 9  # US keyboard 'V'
    send_key_with_modifiers(keycode_a, kCGEventFlagMaskCommand)
    time.sleep(0.05)
    send_key_with_modifiers(keycode_v, kCGEventFlagMaskCommand)


def press_return():
    keycode_return = 36
    event_down = CGEventCreateKeyboardEvent(None, keycode_return, True)
    event_up = CGEventCreateKeyboardEvent(None, keycode_return, False)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


def open_chat_for_contact(contact_name: str) -> None:
    """
    Open a chat for a given contact.

    First, search in the left sidebar session list. If found, click it.
    If not, fall back to typing the name into the global search field
    and pressing Return to select the top result.
    """
    logger.info("Opening chat for contact: %s", contact_name)
    ax_app = get_wechat_ax_app()

    element = find_chat_element_by_name(ax_app, contact_name)
    if element is not None:
        logger.info("Found chat in session list, performing AXPress")
        AXUIElementPerformAction(element, kAXPressAction)
        time.sleep(0.3)
        return

    logger.info("Chat not in session list, using global search")
    focus_and_type_search(ax_app, contact_name)
    time.sleep(0.4)
    press_return()
    time.sleep(0.4)


def get_messages_list(ax_app):
    def is_message_list(el, role, title, identifier):
        return role == kAXListRole and (title or "") == "Messages"

    msg_list = dfs(ax_app, is_message_list)
    if msg_list is None:
        raise RuntimeError("Could not find WeChat 'Messages' list in AX tree")
    return msg_list


def axvalue_to_point(ax_value):
    if ax_value is None or AXValueGetType(ax_value) != kAXValueCGPointType:
        return None
    ok, cg_point = AXValueGetValue(ax_value, kAXValueCGPointType, None)
    if not ok:
        return None
    return float(cg_point.x), float(cg_point.y)


def axvalue_to_size(ax_value):
    if ax_value is None or AXValueGetType(ax_value) != kAXValueCGSizeType:
        return None
    ok, cg_size = AXValueGetValue(ax_value, kAXValueCGSizeType, None)
    if not ok:
        return None
    return float(cg_size.width), float(cg_size.height)


def capture_message_area(msg_list):
    pos_ref = ax_get(msg_list, kAXPositionAttribute)
    size_ref = ax_get(msg_list, kAXSizeAttribute)
    origin = axvalue_to_point(pos_ref)
    size = axvalue_to_size(size_ref)
    if origin is None or size is None:
        raise RuntimeError("Failed to get bounds for WeChat messages list")

    x, y = origin
    w, h = size

    bbox = (int(x), int(y), int(x + w), int(y + h))
    image = ImageGrab.grab(bbox=bbox)
    return image, origin, size


def count_colored_pixels(image, left, top, right, bottom):
    left = max(0, int(left))
    top = max(0, int(top))
    right = min(image.width, int(right))
    bottom = min(image.height, int(bottom))
    if right <= left or bottom <= top:
        return 0, 0

    region = image.crop((left, top, right, bottom)).convert("RGB")
    pixels = region.load()

    width, height = region.size
    colored = 0
    total = width * height

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            brightness = (r + g + b) / 3.0
            if brightness < 20:
                continue
            if brightness > 40 or (max(r, g, b) - min(r, g, b)) > 10:
                colored += 1

    return colored, total


SenderLabel = Literal["ME", "OTHER", "UNKNOWN"]


def classify_sender_for_message(
    image, list_origin, message_pos, message_size
) -> SenderLabel:
    list_x, list_y = list_origin
    msg_x, msg_y = message_pos
    msg_w, msg_h = message_size

    rel_x = msg_x - list_x
    rel_y = msg_y - list_y

    band_height = min(40.0, msg_h)
    center_y = rel_y + msg_h / 2.0
    top = center_y - band_height / 2.0
    bottom = top + band_height

    margin = 5.0
    sample_width = min(100.0, msg_w / 3.0)

    left_left = rel_x + margin
    left_right = left_left + sample_width

    right_right = rel_x + msg_w - margin
    right_left = right_right - sample_width

    left_colored, left_total = count_colored_pixels(
        image, left_left, top, left_right, bottom
    )
    right_colored, right_total = count_colored_pixels(
        image, right_left, top, right_right, bottom
    )

    avg_area = (left_total + right_total) / 2.0 if (left_total + right_total) else 0.0
    min_signal = max(10.0, avg_area * 0.01)

    if left_colored < min_signal and right_colored < min_signal:
        return "UNKNOWN"

    if right_colored > left_colored * 1.5:
        return "ME"
    if left_colored > right_colored * 1.5:
        return "OTHER"
    return "UNKNOWN"


@dataclass
class ChatMessage:
    sender: SenderLabel
    text: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def fetch_recent_messages(last_n: int = 100) -> list[ChatMessage]:
    """
    Fetch recent messages from the currently open chat, classifying
    each message as ME, OTHER, or UNKNOWN using a screenshot-based
    heuristic similar to simple_sender_detection.py.
    """
    ax_app = get_wechat_ax_app()
    msg_list = get_messages_list(ax_app)

    image, list_origin, _ = capture_message_area(msg_list)

    children = ax_get(msg_list, kAXChildrenAttribute) or []
    start = max(0, len(children) - last_n)

    messages: list[ChatMessage] = []

    for child in children[start:]:
        text = ax_get(child, kAXValueAttribute) or ax_get(child, kAXTitleAttribute)
        if not text:
            continue

        pos_ref = ax_get(child, kAXPositionAttribute)
        size_ref = ax_get(child, kAXSizeAttribute)
        point = axvalue_to_point(pos_ref)
        size = axvalue_to_size(size_ref)
        if point is None or size is None:
            sender: SenderLabel = "UNKNOWN"
        else:
            sender = classify_sender_for_message(image, list_origin, point, size)

        messages.append(ChatMessage(sender=sender, text=str(text)))

    logger.info("Fetched %d messages from current chat", len(messages))
    return messages


def find_input_field(ax_app):
    def is_input(el, role, title, identifier):
        return role == kAXTextAreaRole and identifier == "chat_input_field"

    input_field = dfs(ax_app, is_input)
    if input_field is None:
        raise RuntimeError(
            "Could not find WeChat chat input field via Accessibility API"
        )
    return input_field


def send_message(text: str) -> None:
    """
    Send a message in the currently open chat by focusing the input
    field, setting its value, and pressing Return.
    """
    logger.info("Sending message of length %d characters", len(text))
    ax_app = get_wechat_ax_app()
    input_field = find_input_field(ax_app)

    AXUIElementPerformAction(input_field, kAXRaiseAction)

    err = AXUIElementSetAttributeValue(input_field, kAXValueAttribute, text)
    if err != 0:
        raise RuntimeError(f"Failed to set input text, AX error {err}")

    time.sleep(0.1)
    press_return()
    logger.info("Message sent")
