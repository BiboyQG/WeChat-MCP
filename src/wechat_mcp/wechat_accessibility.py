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
    CGEventCreateMouseEvent,
    CGEventCreateScrollWheelEvent,
    CGEventPost,
    CGEventSetFlags,
    CGEventSetLocation,
    CGPoint,
    kCGEventFlagMaskCommand,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGHIDEventTap,
    kCGScrollEventUnitLine,
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


def get_current_chat_name() -> str | None:
    """
    Return the display name of the currently open chat, if available.
    """
    ax_app = get_wechat_ax_app()

    def is_chat_title(el, role, title, identifier):
        return role == kAXStaticTextRole and identifier == "big_title_line_h_view"

    title_el = dfs(ax_app, is_chat_title)
    if title_el is None:
        logger.warning("Could not locate current chat title element via AX")
        return None

    value = ax_get(title_el, kAXValueAttribute)
    if isinstance(value, str) and value.strip():
        return value.strip()

    title = ax_get(title_el, kAXTitleAttribute)
    if isinstance(title, str) and title.strip():
        return title.strip()

    return None


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


def click_element_center(element) -> None:
    """
    Synthesize a left mouse click at the visual center of the element.
    """
    pos_ref = ax_get(element, kAXPositionAttribute)
    size_ref = ax_get(element, kAXSizeAttribute)
    point = axvalue_to_point(pos_ref)
    size = axvalue_to_size(size_ref)
    if point is None or size is None:
        raise RuntimeError("Failed to get bounds for element to click")

    x, y = point
    w, h = size
    cx = x + w / 2.0
    cy = y + h / 2.0

    event_down = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseDown, CGPoint(cx, cy), 0
    )
    event_up = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseUp, CGPoint(cx, cy), 0
    )
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


def open_chat_for_contact(contact_name: str) -> dict[str, Any] | None:
    """
    Open a chat for a given contact.

    First, search in the left sidebar session list. If found, click it.
    If not, type the name into the global search field and inspect the
    search results:
    - Prefer an exact match under the "Contacts" section.
    - Otherwise, prefer an exact match under the "Group Chats" section.
    - If no exact match is visible, expand "View All" for Contacts and
      Group Chats (if present) and scroll through results, looking for
      an exact match while explicitly ignoring the "Chat History", "Official Accounts", and "More" sections.

    If no exact match can be found, this function does **not** fall back
    to the top search result. Instead, it returns a dict of the form:

    {
        "error": "<LLM-friendly message>",
        "contact_name": "<original contact_name>",
        "candidates": {
            "contacts": [... up to 15 names ...],
            "group_chats": [... up to 15 names ...],
        },
    }

    Callers can use this to ask the LLM to choose a more specific target.
    """
    logger.info("Opening chat for contact: %s", contact_name)
    ax_app = get_wechat_ax_app()

    element = find_chat_element_by_name(ax_app, contact_name)
    if element is not None:
        logger.info("Found chat in session list, clicking center")
        click_element_center(element)
        time.sleep(0.3)
        return

    logger.info("Chat not in session list, using global search")
    focus_and_type_search(ax_app, contact_name)
    time.sleep(0.4)

    try:
        found, candidates = _select_contact_from_search_results(
            ax_app, contact_name
        )
        if found:
            logger.info(
                "Opened chat for %s via search results", contact_name
            )
            time.sleep(0.4)
            return None

        logger.info(
            "Exact match for %s not found in Contacts/Group Chats search "
            "results; returning candidate names",
            contact_name,
        )
        error_msg = (
            "Could not find an exact match for the requested contact name in "
            "WeChat's Contacts or Group Chats search results. Returning "
            "related contact and group names so the LLM can choose a more "
            "specific chat to open."
        )
        logger.warning(
            "open_chat_for_contact(%s) returning candidates instead of "
            "opening a chat: %s",
            contact_name,
            error_msg,
        )
        return {
            "error": error_msg,
            "contact_name": contact_name,
            "candidates": candidates,
        }
    except Exception as exc:
        logger.exception(
            "Error while selecting contact %s from search results: %s",
            contact_name,
            exc,
        )
        raise


def get_search_list(ax_app):
    """
    Return the AX list that contains global search results in the
    left sidebar (identifier: 'search_list').
    """

    def is_search_list(el, role, title, identifier):
        return role == kAXListRole and identifier == "search_list"

    search_list = dfs(ax_app, is_search_list)
    if search_list is None:
        raise RuntimeError(
            "Could not find WeChat search results list via Accessibility API"
        )
    return search_list


@dataclass
class SearchEntry:
    element: Any
    text: str
    y: float


def _collect_search_entries(search_list) -> list[SearchEntry]:
    """
    Collect visible static-text entries from the search results list,
    including section headers, result cards and "View All"/"Collapse"
    rows. Entries are sorted by vertical (Y) position.
    """
    entries: list[SearchEntry] = []

    def walk(el):
        role = ax_get(el, kAXRoleAttribute)
        if role == kAXStaticTextRole:
            title = ax_get(el, kAXTitleAttribute)
            value = ax_get(el, kAXValueAttribute)
            text_obj = title if isinstance(title, str) and title else value
            if isinstance(text_obj, str):
                pos_ref = ax_get(el, kAXPositionAttribute)
                point = axvalue_to_point(pos_ref)
                y = point[1] if point is not None else 0.0
                entries.append(
                    SearchEntry(
                        element=el,
                        text=text_obj.strip(),
                        y=float(y),
                    )
                )

        children = ax_get(el, kAXChildrenAttribute) or []
        for child in children:
            walk(child)

    walk(search_list)
    entries.sort(key=lambda e: e.y)
    return entries


def _build_section_headers(entries: list[SearchEntry]) -> dict[str, float]:
    """
    Map known section titles ("Contacts", "Group Chats", "Chat History", "Official Accounts", "More")
    to their vertical Y coordinate within the search list.
    """
    headers: dict[str, float] = {}
    for entry in entries:
        if entry.text in ("Contacts", "Group Chats", "Chat History", "Official Accounts", "More"):
            headers[entry.text] = entry.y
    return headers


def _classify_section(
    entry: SearchEntry, headers: dict[str, float]
) -> str | None:
    """
    Given an entry and the Y positions of section headers, determine which
    section this entry belongs to by picking the last header above it.
    """
    section: str | None = None
    best_y = float("-inf")
    for title, header_y in headers.items():
        if header_y <= entry.y and header_y > best_y:
            section = title
            best_y = header_y
    return section


def _find_exact_match_in_entries(
    entries: list[SearchEntry], contact_name: str
):
    """
    Look for an exact match in the current snapshot of search results.

    Preference order:
    - Exact match under "Contacts"
    - Exact match under "Group Chats"

    Entries classified as "Chat History", "Official Accounts", or "More" are ignored.
    """
    target = contact_name.strip()
    headers = _build_section_headers(entries)

    contact_element = None
    group_element = None

    for entry in entries:
        if entry.text != target:
            continue
        section = _classify_section(entry, headers)
        if section == "Contacts" and contact_element is None:
            contact_element = entry.element
        elif section == "Group Chats" and group_element is None:
            group_element = entry.element

    if contact_element is not None:
        return contact_element
    if group_element is not None:
        return group_element
    return None


def _summarize_search_candidates(
    entries: list[SearchEntry],
) -> dict[str, list[str]]:
    """
    Summarize candidate names from search entries, grouped by section.

    Returns up to 15 unique names from each of:
    - "Contacts"
    - "Group Chats"

    Entries belonging to "Chat History", "Official Accounts", or "More" are ignored.
    """
    headers = _build_section_headers(entries)
    contacts: list[str] = []
    group_chats: list[str] = []

    for entry in entries:
        # Skip section headers themselves.
        if entry.text in ("Contacts", "Group Chats", "Chat History", "Official Accounts", "More"):
            continue

        section = _classify_section(entry, headers)
        if section == "Contacts":
            if entry.text not in contacts:
                contacts.append(entry.text)
        elif section == "Group Chats":
            if entry.text not in group_chats:
                group_chats.append(entry.text)

    return {
        "contacts": contacts[:15],
        "group_chats": group_chats[:15],
    }


def _expand_section_if_needed(search_list, section_title: str) -> None:
    """
    If a "View All(...)" row exists for the given section title
    ("Contacts" or "Group Chats"), click its center to expand that section.
    """
    entries = _collect_search_entries(search_list)
    headers = _build_section_headers(entries)
    if section_title not in headers:
        return

    for entry in entries:
        if not entry.text.startswith("View All"):
            continue
        section = _classify_section(entry, headers)
        if section == section_title:
            logger.info("Expanding %s section via %r", section_title, entry.text)
            click_element_center(entry.element)
            time.sleep(0.3)
            return


def _select_contact_from_search_results(
    ax_app, contact_name: str
) -> tuple[bool, dict[str, list[str]]]:
    """
    Try to open a chat by selecting an exact match from the global
    search results list, preferring Contacts over Group Chats and
    ignoring the Chat History, Official Accounts, and More sections.
    """
    search_list = get_search_list(ax_app)

    aggregated_contacts: set[str] = set()
    aggregated_groups: set[str] = set()

    def update_candidates(entries: list[SearchEntry]) -> None:
        partial = _summarize_search_candidates(entries)
        aggregated_contacts.update(partial["contacts"])
        aggregated_groups.update(partial["group_chats"])

    # First, inspect the initial compact search popover without scrolling.
    entries = _collect_search_entries(search_list)
    update_candidates(entries)
    element = _find_exact_match_in_entries(entries, contact_name)
    if element is not None:
        logger.info(
            "Found exact match for %s in initial search results", contact_name
        )
        click_element_center(element)
        return True, {
            "contacts": list(aggregated_contacts)[:15],
            "group_chats": list(aggregated_groups)[:15],
        }

    # No exact match visible yet; expand Contacts and Group Chats if possible.
    _expand_section_if_needed(search_list, "Contacts")
    _expand_section_if_needed(search_list, "Group Chats")

    center = get_list_center(search_list)
    last_bottom_text = None
    stable = 0

    # Scroll through the expanded search list, looking for an
    # exact match under Contacts/Group Chats, while aggregating
    # candidate names from Contacts and Group Chats.
    for _ in range(80):
        entries = _collect_search_entries(search_list)
        update_candidates(entries)

        element = _find_exact_match_in_entries(entries, contact_name)
        if element is not None:
            logger.info(
                "Found exact match for %s while scrolling search results",
                contact_name,
            )
            click_element_center(element)
            return True, {
                "contacts": list(aggregated_contacts)[:15],
                "group_chats": list(aggregated_groups)[:15],
            }

        children = ax_get(search_list, kAXChildrenAttribute) or []
        texts: list[str] = []
        for child in children:
            txt = ax_get(child, kAXValueAttribute) or ax_get(
                child, kAXTitleAttribute
            )
            if isinstance(txt, str) and txt.strip():
                texts.append(txt)

        if not texts:
            break

        new_last = texts[-1]
        if new_last == last_bottom_text:
            stable += 1
            if stable >= 3:
                break
        else:
            last_bottom_text = new_last
            stable = 0

        # Positive delta scrolls downwards through the search results list.
        post_scroll(center, 80)
        time.sleep(0.1)

    return False, {
        "contacts": list(aggregated_contacts)[:15],
        "group_chats": list(aggregated_groups)[:15],
    }


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


def get_list_center(msg_list):
    """
    Compute the on-screen center point of the messages list, used as
    the target for scroll-wheel events.
    """
    pos_ref = ax_get(msg_list, kAXPositionAttribute)
    size_ref = ax_get(msg_list, kAXSizeAttribute)
    origin = axvalue_to_point(pos_ref)
    size = axvalue_to_size(size_ref)
    if origin is None or size is None:
        raise RuntimeError("Failed to get bounds for WeChat messages list")

    x, y = origin
    w, h = size
    return x + w / 2.0, y + h / 2.0


def post_scroll(center, delta_lines: int) -> None:
    """
    Post a scroll-wheel event at the given screen position.

    Positive delta_lines scrolls towards newer messages (bottom of history),
    negative towards older messages (top of history).
    """
    cx, cy = center
    event = CGEventCreateScrollWheelEvent(
        None, kCGScrollEventUnitLine, 1, delta_lines
    )
    CGEventSetLocation(event, CGPoint(cx, cy))
    CGEventPost(kCGHIDEventTap, event)


def scroll_to_bottom(msg_list, center) -> None:
    """
    Scroll the messages list to the bottom (newest messages) by repeatedly
    sending large positive scroll events until the last visible message
    stabilizes.
    """
    last_text = None
    stable = 0

    for _ in range(40):
        # Positive delta moves towards newer messages (bottom of history).
        post_scroll(center, 1000)
        time.sleep(0.05)

        children = ax_get(msg_list, kAXChildrenAttribute) or []
        texts: list[str] = []
        for child in children:
            txt = ax_get(child, kAXValueAttribute) or ax_get(
                child, kAXTitleAttribute
            )
            if txt:
                texts.append(txt)
        if not texts:
            continue

        new_last = texts[-1]
        if new_last == last_text:
            stable += 1
            if stable >= 3:
                break
        else:
            last_text = new_last
            stable = 0

    time.sleep(0.2)


def scroll_up_small(center) -> None:
    """
    Scroll slightly upwards to reveal older messages.
    """
    # Negative delta scrolls towards older messages.
    post_scroll(center, -50)
    time.sleep(0.1)


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


def fetch_recent_messages(
    last_n: int = 100, max_scrolls: int = 80
) -> list[ChatMessage]:
    """
    Fetch the true last N messages from the currently open chat, even
    when the history spans multiple screens.

    Uses a scrolling strategy that involves:
    - Scrolls to the bottom of the chat history.
    - Repeatedly scrolls upwards in small steps.
    - At each position, captures a screenshot of the message area and
      collects all visible messages plus their positions/sizes.
    - Classifies each message as ME/OTHER/UNKNOWN using the same
      screenshot-based heuristic as before.
    - Merges newly revealed older messages at the front of the list by
      aligning on the oldest already-known message text.
    """
    ax_app = get_wechat_ax_app()
    msg_list = get_messages_list(ax_app)
    center = get_list_center(msg_list)
    scroll_to_bottom(msg_list, center)

    messages: list[ChatMessage] = []
    no_new_counter = 0

    for _ in range(max_scrolls):
        image, list_origin, _ = capture_message_area(msg_list)

        children = ax_get(msg_list, kAXChildrenAttribute) or []
        visible: list[ChatMessage] = []

        for child in children:
            text = ax_get(child, kAXValueAttribute) or ax_get(
                child, kAXTitleAttribute
            )
            if not text:
                continue

            pos_ref = ax_get(child, kAXPositionAttribute)
            size_ref = ax_get(child, kAXSizeAttribute)
            point = axvalue_to_point(pos_ref)
            size = axvalue_to_size(size_ref)
            if point is None or size is None:
                sender: SenderLabel = "UNKNOWN"
            else:
                sender = classify_sender_for_message(
                    image, list_origin, point, size
                )

            visible.append(ChatMessage(sender=sender, text=str(text)))

        if not visible:
            break

        if not messages:
            messages = visible
        else:
            # Align on the oldest already-known message using its text as anchor.
            anchor_text = messages[0].text
            idx = None
            for i, msg in enumerate(visible):
                if msg.text == anchor_text:
                    idx = i
                    break

            if idx is None:
                new_older = visible
            else:
                new_older = visible[:idx]

            if new_older:
                messages = new_older + messages
                no_new_counter = 0
            else:
                no_new_counter += 1
                if no_new_counter >= 5:
                    break

        if len(messages) >= last_n:
            break

        scroll_up_small(center)

    if len(messages) > last_n:
        messages = messages[-last_n:]

    logger.info(
        "Fetched %d messages from current chat (requested last_n=%d)",
        len(messages),
        last_n,
    )
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
