from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable

import AppKit
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    AXValueGetType,
    AXValueGetValue,
    kAXButtonRole,
    kAXChildrenAttribute,
    kAXIdentifierAttribute,
    kAXListRole,
    kAXMenuBarRole,
    kAXMenuBarItemRole,
    kAXMenuItemRole,
    kAXPositionAttribute,
    kAXPressAction,
    kAXRaiseAction,
    kAXRoleAttribute,
    kAXSizeAttribute,
    kAXStaticTextRole,
    kAXSubroleAttribute,
    kAXTextAreaRole,
    kAXTitleAttribute,
    kAXValueAttribute,
    kAXValueCGPointType,
    kAXValueCGSizeType,
    kAXWindowRole,
    kAXWindowsAttribute,
)
from Quartz import (
    CGEventCreate,
    CGEventCreateKeyboardEvent,
    CGEventCreateMouseEvent,
    CGEventCreateScrollWheelEvent,
    CGEventGetLocation,
    CGEventPost,
    CGEventSetFlags,
    CGEventSetLocation,
    CGPoint,
    kCGEventFlagMaskCommand,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGHIDEventTap,
    kCGScrollEventUnitLine,
)

import Quartz

from .logging_config import logger

# ---------------------------------------------------------------------------
# Constants describing the WeChat 4.x (Qt based) macOS client.
#
# Verified against WeChat 4.1.13 with the English UI. Chinese titles are
# included as best-effort fallbacks for clients running in Chinese.
# ---------------------------------------------------------------------------

WECHAT_BUNDLE_ID = "com.tencent.xinWeChat"

MAIN_WINDOW_TITLES = ("WeChat", "Weixin", "微信")
SEARCH_FIELD_TITLES = ("Search", "搜索")
CHATS_TAB_TITLES = ("WeChat", "Weixin", "微信", "Chats")
WINDOW_MENU_TITLES = ("Window", "窗口")
CHATS_MENU_ITEM_TITLES = ("Chats", "聊天")

# Identifiers exposed by WeChat 4.x through the Accessibility API.
ID_MAIN_SPLITTER = "main_window_main_splitter_view"
ID_SESSION_LIST = "session_list"
ID_SESSION_ITEM_PREFIX = "session_item_"
ID_SEARCH_LIST = "search_list"
ID_SEARCH_ITEM_PREFIX = "search_item_"
ID_CHAT_TITLE = "big_title_line_h_view"
ID_CHAT_NAME_LABEL = "current_chat_name_label"
ID_CHAT_INPUT = "chat_input_field"
ID_MESSAGE_LIST = "chat_message_list"

# Section headers shown in the global search popover.
SEARCH_SECTION_CONTACTS = ("Contacts", "联系人")
SEARCH_SECTION_GROUPS = ("Group Chats", "群聊")
SEARCH_SECTION_HEADERS = (
    *SEARCH_SECTION_CONTACTS,
    *SEARCH_SECTION_GROUPS,
    "Chat History",
    "Official Accounts",
    "Service Accounts",
    "Internet search results",
    "Mini Programs",
    "Channels",
    "More",
    "聊天记录",
    "公众号",
    "服务号",
    "网络搜索结果",
    "小程序",
    "视频号",
    "更多",
)
# Headers shown while the popover still displays recent searches rather
# than results for the current query.
SEARCH_PLACEHOLDER_HEADERS = (
    "Recent Searches",
    "Search Results",
    "最近搜索",
    "搜索结果",
)

KEYCODE_A = 0
KEYCODE_V = 9
KEYCODE_RETURN = 36
KEYCODE_ESCAPE = 53


# ---------------------------------------------------------------------------
# Low level AX helpers
# ---------------------------------------------------------------------------


def ax_get(element, attribute):
    if element is None:
        return None
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if err != 0:
        return None
    return value


def dfs(element, predicate: Callable[[Any, Any, Any, Any], bool]):
    """
    Depth-first search of the AX tree rooted at ``element``. The predicate
    receives ``(element, role, title, identifier)``.
    """
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


def find_by_identifier(root, identifier: str, role: str | None = None):
    """Return the first descendant whose AXIdentifier equals ``identifier``."""

    def match(el, el_role, title, el_identifier):
        if el_identifier != identifier:
            return False
        return role is None or el_role == role

    return dfs(root, match)


def axvalue_to_point(ax_value):
    if ax_value is None:
        return None
    if isinstance(ax_value, (tuple, list)) and len(ax_value) == 2:
        return float(ax_value[0]), float(ax_value[1])
    if AXValueGetType(ax_value) != kAXValueCGPointType:
        return None
    ok, cg_point = AXValueGetValue(ax_value, kAXValueCGPointType, None)
    if not ok:
        return None
    return float(cg_point.x), float(cg_point.y)


def axvalue_to_size(ax_value):
    if ax_value is None:
        return None
    if isinstance(ax_value, (tuple, list)) and len(ax_value) == 2:
        return float(ax_value[0]), float(ax_value[1])
    if AXValueGetType(ax_value) != kAXValueCGSizeType:
        return None
    ok, cg_size = AXValueGetValue(ax_value, kAXValueCGSizeType, None)
    if not ok:
        return None
    return float(cg_size.width), float(cg_size.height)


def element_frame(element) -> tuple[float, float, float, float] | None:
    """Return ``(x, y, w, h)`` for the element, or None if unavailable."""
    point = axvalue_to_point(ax_get(element, kAXPositionAttribute))
    size = axvalue_to_size(ax_get(element, kAXSizeAttribute))
    if point is None or size is None:
        return None
    return point[0], point[1], size[0], size[1]


def element_text(element) -> str | None:
    """Return the AXTitle, falling back to a string AXValue."""
    title = ax_get(element, kAXTitleAttribute)
    if isinstance(title, str) and title:
        return title
    value = ax_get(element, kAXValueAttribute)
    if isinstance(value, str) and value:
        return value
    return None


def get_list_center(msg_list):
    """
    Compute the on-screen center point of a list element, used as the
    target for scroll-wheel events.
    """
    frame = element_frame(msg_list)
    if frame is None:
        raise RuntimeError("Failed to get bounds for list element")
    x, y, w, h = frame
    return x + w / 2.0, y + h / 2.0


# ---------------------------------------------------------------------------
# Input synthesis
# ---------------------------------------------------------------------------


def send_key_with_modifiers(keycode: int, flags: int = 0):
    event_down = CGEventCreateKeyboardEvent(None, keycode, True)
    CGEventSetFlags(event_down, flags)
    event_up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(event_up, flags)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


def press_escape() -> None:
    send_key_with_modifiers(KEYCODE_ESCAPE, 0)


def press_return() -> None:
    send_key_with_modifiers(KEYCODE_RETURN, 0)


def paste_text(text: str) -> None:
    """
    Put ``text`` on the general pasteboard and press Command+A then
    Command+V so it replaces the content of the focused text field.
    """
    pb = AppKit.NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, AppKit.NSPasteboardTypeString)
    time.sleep(0.1)
    send_key_with_modifiers(KEYCODE_A, kCGEventFlagMaskCommand)
    time.sleep(0.05)
    send_key_with_modifiers(KEYCODE_V, kCGEventFlagMaskCommand)


def click_at(cx: float, cy: float) -> None:
    event_down = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseDown, CGPoint(cx, cy), 0
    )
    event_up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, CGPoint(cx, cy), 0)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


def click_element_center(element) -> None:
    """
    Synthesize a left mouse click at the visual center of the element.
    """
    frame = element_frame(element)
    if frame is None:
        raise RuntimeError("Failed to get bounds for element to click")
    x, y, w, h = frame
    click_at(x + w / 2.0, y + h / 2.0)


def long_press_element_center(element, hold_seconds: float = 2.2) -> None:
    """
    Synthesize a long left mouse press at the visual center of the
    given element.
    """
    frame = element_frame(element)
    if frame is None:
        raise RuntimeError("Failed to get bounds for element to long-press")
    x, y, w, h = frame
    cx = x + w / 2.0
    cy = y + h / 2.0

    event_down = CGEventCreateMouseEvent(
        None, kCGEventLeftMouseDown, CGPoint(cx, cy), 0
    )
    CGEventPost(kCGHIDEventTap, event_down)
    try:
        time.sleep(max(0.0, hold_seconds))
    finally:
        event_up = CGEventCreateMouseEvent(
            None, kCGEventLeftMouseUp, CGPoint(cx, cy), 0
        )
        CGEventPost(kCGHIDEventTap, event_up)


def get_mouse_location() -> tuple[float, float]:
    """Current pointer position in screen (top-left origin) coordinates."""
    point = CGEventGetLocation(CGEventCreate(None))
    return float(point.x), float(point.y)


def move_mouse(cx: float, cy: float) -> None:
    """
    Warp the pointer. Scroll-wheel events are delivered to the window under
    the *actual* pointer, not to the event's location, so the pointer must
    be over the list before scrolling it.
    """
    event = CGEventCreateMouseEvent(None, kCGEventMouseMoved, CGPoint(cx, cy), 0)
    CGEventPost(kCGHIDEventTap, event)


def post_scroll(center, delta_lines: int) -> None:
    """
    Post a scroll-wheel event over the given screen position.

    On a standard macOS configuration:
    - Positive delta_lines scrolls towards older content (upwards in history).
    - Negative delta_lines scrolls towards newer content (downwards in history).
    """
    cx, cy = center
    # Always send a mouse-moved event first: Qt routes wheel events to the
    # widget it last saw the pointer over, and a pointer that merely sits
    # at the right spot (without a move event) is not enough.
    move_mouse(cx, cy)
    event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, delta_lines)
    CGEventSetLocation(event, CGPoint(cx, cy))
    CGEventPost(kCGHIDEventTap, event)


def set_text_value(element, text: str, click_fallback: bool = True) -> bool:
    """
    Set the text of an AX text element.

    WeChat 4.x accepts AXValue writes on its text areas, which is the
    fastest and most reliable path. When the write is not reflected in
    the element's value, fall back to clicking the element and pasting
    via the clipboard.
    """
    AXUIElementPerformAction(element, kAXRaiseAction)
    err = AXUIElementSetAttributeValue(element, kAXValueAttribute, text)
    time.sleep(0.15)
    if err == 0 and ax_get(element, kAXValueAttribute) == text:
        return True
    logger.debug(
        "AX set value did not stick (err=%s); falling back to clipboard paste",
        err,
    )
    if not click_fallback:
        return False
    click_element_center(element)
    time.sleep(0.3)
    paste_text(text)
    time.sleep(0.4)
    return ax_get(element, kAXValueAttribute) == text


# ---------------------------------------------------------------------------
# Application / window discovery
# ---------------------------------------------------------------------------


def get_wechat_running_app():
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        WECHAT_BUNDLE_ID
    )
    if not apps:
        raise RuntimeError("WeChat is not running")
    return apps[0]


def get_wechat_pid() -> int:
    return int(get_wechat_running_app().processIdentifier())


def get_frontmost_bundle_id() -> str | None:
    """
    Bundle id of the application that owns the frontmost normal window.

    NSWorkspace's frontmostApplication is only refreshed by a run loop,
    which a plain Python process does not spin, so the window server's
    front-to-back window list is consulted instead.
    """
    options = (
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements
    )
    infos = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []
    for info in infos:
        if int(info.get(Quartz.kCGWindowLayer, 0)) != 0:
            continue
        pid = int(info.get(Quartz.kCGWindowOwnerPID, -1))
        app = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is not None and app.bundleIdentifier():
            return app.bundleIdentifier()
    front = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return front.bundleIdentifier() if front is not None else None


def is_wechat_frontmost() -> bool:
    return get_frontmost_bundle_id() == WECHAT_BUNDLE_ID


def activate_bundle(bundle_id: str, timeout: float = 1.5) -> bool:
    """Bring the application with ``bundle_id`` to the foreground."""
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        bundle_id
    )
    if not apps:
        return False
    apps[0].activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
    end = time.time() + timeout
    while time.time() < end:
        if get_frontmost_bundle_id() == bundle_id:
            return True
        time.sleep(0.05)
    return get_frontmost_bundle_id() == bundle_id


def activate_wechat() -> None:
    """Bring WeChat to the foreground so synthetic input reaches it."""
    if is_wechat_frontmost():
        return
    if activate_bundle(WECHAT_BUNDLE_ID):
        logger.info("Activated WeChat")
    else:
        logger.warning("WeChat did not become the frontmost application")


def get_wechat_ax_app(activate: bool = True) -> Any:
    """
    Get the AX UI element representing the WeChat application. With
    ``activate`` (default) WeChat is brought to the foreground first,
    which is required before posting keyboard, mouse or scroll events.
    Pure Accessibility reads work without activation.
    """
    app = get_wechat_running_app()
    if activate:
        activate_wechat()
    return AXUIElementCreateApplication(app.processIdentifier())


def get_windows(ax_app: Any) -> list[Any]:
    return list(ax_get(ax_app, kAXWindowsAttribute) or [])


def get_main_window(ax_app: Any):
    """
    Return the main WeChat window.

    Prefers a standard window whose title is "WeChat"/"微信"; falls back
    to whichever window hosts the main splitter view. Other windows
    (search popover, "Add Contacts", ...) are never returned.
    """
    windows = get_windows(ax_app)
    for window in windows:
        title = ax_get(window, kAXTitleAttribute)
        subrole = ax_get(window, kAXSubroleAttribute)
        if title in MAIN_WINDOW_TITLES and subrole == "AXStandardWindow":
            return window
    for window in windows:
        if find_by_identifier(window, ID_MAIN_SPLITTER) is not None:
            return window
    for window in windows:
        if ax_get(window, kAXSubroleAttribute) == "AXStandardWindow":
            return window
    raise RuntimeError("Could not find the main WeChat window via Accessibility API")


def _find_window_by_title(ax_app: Any, title: str):
    """
    Locate a top-level WeChat window with the given title.
    """
    for window in get_windows(ax_app):
        current = ax_get(window, kAXTitleAttribute)
        if ax_get(window, kAXRoleAttribute) == kAXWindowRole and current == title:
            return window
    return None


def _wait_for_window(ax_app: Any, title: str, timeout: float = 5.0):
    """
    Wait for a window with the given title to appear, returning the AX
    element or None if the timeout expires.
    """
    end = time.time() + timeout
    while time.time() < end:
        window = _find_window_by_title(ax_app, title)
        if window is not None:
            logger.info("Found window %r", title)
            return window
        time.sleep(0.1)
    logger.warning("Timed out waiting for window %r", title)
    return None


def _press_menu_item(ax_app: Any, menu_titles: tuple[str, ...], item_titles: tuple[str, ...]) -> bool:
    """Press ``item`` inside the application's top-level ``menu``."""

    def is_menu_bar(el, role, title, identifier):
        return role == kAXMenuBarRole

    menu_bar = dfs(ax_app, is_menu_bar)
    if menu_bar is None:
        return False

    for bar_item in ax_get(menu_bar, kAXChildrenAttribute) or []:
        if ax_get(bar_item, kAXRoleAttribute) != kAXMenuBarItemRole:
            continue
        if ax_get(bar_item, kAXTitleAttribute) not in menu_titles:
            continue

        def is_item(el, role, title, identifier):
            return role == kAXMenuItemRole and title in item_titles

        item = dfs(bar_item, is_item)
        if item is None:
            return False
        err = AXUIElementPerformAction(item, kAXPressAction)
        return err == 0
    return False


def ensure_chats_tab(ax_app: Any, timeout: float = 3.0) -> Any:
    """
    Make sure the main window shows the Chats tab (session list + search
    field). WeChat 4.x renders Contacts/Discover/Moments inside the same
    window, so the session list disappears when another tab is active.

    Returns the main window element.
    """
    main_window = get_main_window(ax_app)
    if find_by_identifier(main_window, ID_SESSION_LIST) is not None:
        return main_window

    logger.info("Chats tab not active; switching to it")

    win_frame = element_frame(main_window)

    def is_chats_tab(el, role, title, identifier):
        if role != kAXButtonRole or title not in CHATS_TAB_TITLES:
            return False
        frame = element_frame(el)
        if frame is None or win_frame is None:
            return False
        # Tab bar buttons sit at the very left edge of the main window.
        return frame[0] - win_frame[0] < 80 and frame[2] <= 80

    tab = dfs(main_window, is_chats_tab)
    if tab is not None:
        click_element_center(tab)
    elif not _press_menu_item(ax_app, WINDOW_MENU_TITLES, CHATS_MENU_ITEM_TITLES):
        raise RuntimeError("Could not switch WeChat to the Chats tab")

    end = time.time() + timeout
    while time.time() < end:
        if find_by_identifier(main_window, ID_SESSION_LIST) is not None:
            time.sleep(0.2)
            return main_window
        time.sleep(0.1)
    raise RuntimeError("Chats tab did not become active")


# ---------------------------------------------------------------------------
# Current chat / session list
# ---------------------------------------------------------------------------


def _normalize_chat_title(name: str) -> str:
    """
    Normalize a WeChat chat title.

    In particular, strip a trailing "(<digits>)" suffix that WeChat
    appends for group chats to indicate member count, e.g.:
    "My Group(23)" -> "My Group".
    """
    name = name.strip()
    name = re.sub(r"\(\d+\)$", "", name).strip()
    return name


def chat_names_match(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return False
    return _normalize_chat_title(a).casefold() == _normalize_chat_title(b).casefold()


def get_current_chat_name(ax_app: Any | None = None) -> str | None:
    """
    Return the display name of the currently open chat, if available.
    """
    if ax_app is None:
        ax_app = get_wechat_ax_app()
    try:
        main_window = get_main_window(ax_app)
    except RuntimeError:
        return None

    # WeChat 4.x exposes the bare chat name separately from the member count.
    name_el = find_by_identifier(main_window, ID_CHAT_NAME_LABEL)
    if name_el is not None:
        value = ax_get(name_el, kAXValueAttribute) or ax_get(name_el, kAXTitleAttribute)
        if isinstance(value, str) and value.strip():
            return _normalize_chat_title(value)

    title_el = find_by_identifier(main_window, ID_CHAT_TITLE)
    if title_el is None:
        logger.warning("Could not locate current chat title element via AX")
        return None

    value = ax_get(title_el, kAXValueAttribute) or ax_get(title_el, kAXTitleAttribute)
    if isinstance(value, str) and value.strip():
        return _normalize_chat_title(value)
    return None


def get_session_list(main_window: Any):
    session_list = find_by_identifier(main_window, ID_SESSION_LIST)
    if session_list is None:
        raise RuntimeError("Could not find WeChat session list via Accessibility API")
    return session_list


def _visible_session_items(session_list) -> dict[str, Any]:
    """
    Return the session items currently rendered in the (virtualised)
    session list, keyed by chat display name.
    """
    list_frame = element_frame(session_list)
    results: dict[str, Any] = {}
    for child in ax_get(session_list, kAXChildrenAttribute) or []:
        identifier = ax_get(child, kAXIdentifierAttribute)
        if not isinstance(identifier, str) or not identifier.startswith(
            ID_SESSION_ITEM_PREFIX
        ):
            continue
        chat_name = identifier[len(ID_SESSION_ITEM_PREFIX) :]
        if not chat_name:
            continue
        frame = element_frame(child)
        if frame is None or list_frame is None:
            continue
        # Only keep rows that are fully inside the list viewport so that
        # a click lands on the intended row.
        if frame[1] < list_frame[1] - 1 or frame[1] + frame[3] > list_frame[1] + list_frame[3] + 1:
            continue
        results[chat_name] = child
    return results


def scroll_list_to_top(session_list, center, max_rounds: int = 150) -> None:
    """
    Scroll a (virtualised) list to its top, stopping once the visible
    rows no longer change. A fixed number of wheel events is not enough
    for long session lists.
    """
    last: tuple[str, ...] | None = None
    stable = 0
    for _ in range(max_rounds):
        for _ in range(4):
            post_scroll(center, 200)
            time.sleep(0.01)
        time.sleep(0.08)
        signature = tuple(_visible_session_items(session_list).keys())
        if signature == last:
            stable += 1
            if stable >= 2:
                return
        else:
            stable = 0
            last = signature


def collect_chat_elements(ax_app) -> dict[str, Any]:
    """
    Collect the currently visible chat elements from the left session
    list keyed by display name.
    """
    main_window = ensure_chats_tab(ax_app)
    session_list = get_session_list(main_window)
    results = _visible_session_items(session_list)
    logger.info("Collected %d visible chat elements from session list", len(results))
    return results


@dataclass
class SessionRow:
    name: str
    preview: str | None
    time: str | None
    muted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "preview": self.preview,
            "time": self.time,
            "muted": self.muted,
        }


MUTE_MARKERS = ("Mute Notifications", "消息免打扰")


def parse_session_title(name: str, title: str | None) -> SessionRow:
    """
    Parse the multi-line AXTitle of a session row. WeChat 4.x renders
    "<name>\n<preview>\n<time>\n[Mute Notifications\n]".
    """
    lines = [ln for ln in (title or "").split("\n")]
    # Drop trailing empties.
    while lines and not lines[-1].strip():
        lines.pop()
    muted = any(ln.strip() in MUTE_MARKERS for ln in lines)
    body = [ln for ln in lines if ln.strip() not in MUTE_MARKERS]
    if body and body[0].strip() == name.strip():
        body = body[1:]
    preview: str | None = None
    when: str | None = None
    if len(body) >= 2:
        preview = body[0].strip() or None
        when = body[-1].strip() or None
    elif len(body) == 1:
        # Either only a time (empty chat) or only a preview.
        candidate = body[0].strip()
        if re.fullmatch(r"[\d:/\-\s]+|[A-Za-z]+day|Yesterday|昨天|星期.|周.", candidate):
            when = candidate
        else:
            preview = candidate
    return SessionRow(name=name, preview=preview, time=when, muted=muted)


def _visible_session_rows(session_list) -> list[tuple[str, Any]]:
    """Visible session rows in top-to-bottom order as (name, element)."""
    items = _visible_session_items(session_list)
    ordered = sorted(
        items.items(),
        key=lambda kv: (element_frame(kv[1]) or (0.0, 0.0, 0.0, 0.0))[1],
    )
    return ordered


def list_session_chats(ax_app, max_chats: int = 30, scroll: bool = True) -> list[SessionRow]:
    """
    Return the chats in the left session list (most recent first), with
    the last-message preview, time and mute state that WeChat exposes in
    each row. When ``scroll`` is set, the list is scrolled from the top
    to collect more rows than fit on screen.
    """
    main_window = ensure_chats_tab(ax_app)
    session_list = get_session_list(main_window)

    rows: list[SessionRow] = []
    seen: set[str] = set()

    def collect() -> int:
        added = 0
        for name, el in _visible_session_rows(session_list):
            if name in seen:
                continue
            seen.add(name)
            rows.append(parse_session_title(name, ax_get(el, kAXTitleAttribute)))
            added += 1
        return added

    if not scroll:
        collect()
        return rows[:max_chats]

    center = get_list_center(session_list)
    scroll_list_to_top(session_list, center)

    stale = 0
    for _ in range(400):
        added = collect()
        if len(rows) >= max_chats:
            break
        stale = stale + 1 if added == 0 else 0
        if stale >= 4:
            break
        post_scroll(center, -8)
        time.sleep(0.12)

    # Leave the list where the user expects it: at the top.
    scroll_list_to_top(session_list, center)
    return rows[:max_chats]


def _lookup_chat(elements: dict[str, Any], chat_name: str):
    if chat_name in elements:
        return elements[chat_name]
    wanted = chat_name.casefold()
    for name, el in elements.items():
        if name.casefold() == wanted:
            return el
    return None


def find_chat_element_by_name(ax_app, chat_name: str, scroll: bool = True):
    """
    Find a session-list row whose name matches ``chat_name`` (exact,
    then case-insensitive).

    The session list in WeChat 4.x is virtualised and only exposes the
    rows that are currently rendered, so when the chat is not visible
    the list is scrolled from the top to the bottom while looking for it.
    """
    main_window = ensure_chats_tab(ax_app)
    session_list = get_session_list(main_window)

    element = _lookup_chat(_visible_session_items(session_list), chat_name)
    if element is not None or not scroll:
        return element

    center = get_list_center(session_list)
    scroll_list_to_top(session_list, center)

    last_signature: tuple[str, ...] | None = None
    stable = 0
    for _ in range(400):
        visible = _visible_session_items(session_list)
        element = _lookup_chat(visible, chat_name)
        if element is not None:
            logger.info("Found chat %r in session list after scrolling", chat_name)
            return element

        signature = tuple(visible.keys())
        if signature == last_signature:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = 0
            last_signature = signature

        post_scroll(center, -8)
        time.sleep(0.12)

    return None


# ---------------------------------------------------------------------------
# Global search
# ---------------------------------------------------------------------------


def find_search_field(ax_app):
    """
    Locate the sidebar search field in the main window.
    """
    main_window = ensure_chats_tab(ax_app)

    def is_search(el, role, title, identifier):
        return role == kAXTextAreaRole and title in SEARCH_FIELD_TITLES

    search = dfs(main_window, is_search)
    if search is None:
        raise RuntimeError(
            "Could not find WeChat search text field via Accessibility API"
        )
    return search


def get_search_list(ax_app):
    """
    Return the AX list that contains global search results. WeChat 4.x
    renders it inside a separate popover window (AXDialog).
    """

    def is_search_list(el, role, title, identifier):
        return role == kAXListRole and identifier == ID_SEARCH_LIST

    search_list = dfs(ax_app, is_search_list)
    if search_list is None:
        raise RuntimeError(
            "Could not find WeChat search results list via Accessibility API"
        )
    return search_list


def _search_list_or_none(ax_app):
    try:
        return get_search_list(ax_app)
    except RuntimeError:
        return None


def close_search(ax_app) -> None:
    """Dismiss the search popover (if open) and clear the query."""
    if _search_list_or_none(ax_app) is not None:
        press_escape()
        time.sleep(0.3)


def wait_for_search_results(ax_app, timeout: float = 4.0):
    """
    Wait until the search popover shows results for the current query
    (as opposed to the "Recent Searches" placeholder). Returns the
    search list element or None on timeout.
    """
    end = time.time() + timeout
    search_list = None
    while time.time() < end:
        search_list = _search_list_or_none(ax_app)
        if search_list is not None:
            titles = [
                element_text(child) or ""
                for child in ax_get(search_list, kAXChildrenAttribute) or []
            ]
            if titles and not any(t in SEARCH_PLACEHOLDER_HEADERS for t in titles):
                return search_list
        time.sleep(0.15)
    return search_list


def focus_and_type_search(ax_app, text: str):
    """
    Put ``text`` into the sidebar search field and wait for results.
    """
    close_search(ax_app)
    search = find_search_field(ax_app)

    err = AXUIElementSetAttributeValue(search, kAXValueAttribute, "")
    if err != 0:
        logger.debug("Failed to clear search field via AX (err=%s)", err)
    time.sleep(0.15)

    if not set_text_value(search, text):
        raise RuntimeError("Could not enter text into the WeChat search field")

    if wait_for_search_results(ax_app) is None:
        logger.warning("Search results did not appear for query %r", text)


@dataclass
class SearchEntry:
    element: Any
    text: str
    y: float
    identifier: str = ""


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
            text_obj = element_text(el)
            if isinstance(text_obj, str):
                point = axvalue_to_point(ax_get(el, kAXPositionAttribute))
                y = point[1] if point is not None else 0.0
                identifier = ax_get(el, kAXIdentifierAttribute)
                entries.append(
                    SearchEntry(
                        element=el,
                        text=text_obj.strip(),
                        y=float(y),
                        identifier=identifier if isinstance(identifier, str) else "",
                    )
                )

        children = ax_get(el, kAXChildrenAttribute) or []
        for child in children:
            walk(child)

    walk(search_list)
    entries.sort(key=lambda e: e.y)
    return entries


def _is_section_header(entry: SearchEntry) -> bool:
    return not entry.identifier and entry.text in SEARCH_SECTION_HEADERS


def _build_section_headers(entries: list[SearchEntry]) -> dict[str, float]:
    """
    Map known section titles to their vertical Y coordinate within the
    search list.
    """
    headers: dict[str, float] = {}
    for entry in entries:
        if _is_section_header(entry):
            headers[entry.text] = entry.y
    return headers


def _classify_section(entry: SearchEntry, headers: dict[str, float]) -> str | None:
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


def _entry_matches_name(entry: SearchEntry, target: str) -> bool:
    if entry.identifier:
        if not entry.identifier.startswith(ID_SEARCH_ITEM_PREFIX):
            return False
        name = entry.identifier[len(ID_SEARCH_ITEM_PREFIX) :]
        return name == target or name.casefold() == target.casefold()
    return entry.text == target


def _find_exact_match_in_entries(entries: list[SearchEntry], contact_name: str):
    """
    Look for an exact match in the current snapshot of search results.

    Preference order:
    - Exact match under "Contacts"
    - Exact match under "Group Chats"

    Entries under any other section are ignored.
    """
    target = contact_name.strip()
    headers = _build_section_headers(entries)

    contact_element = None
    group_element = None

    for entry in entries:
        if _is_section_header(entry) or not _entry_matches_name(entry, target):
            continue
        section = _classify_section(entry, headers)
        if section in SEARCH_SECTION_CONTACTS and contact_element is None:
            contact_element = entry.element
        elif section in SEARCH_SECTION_GROUPS and group_element is None:
            group_element = entry.element

    if contact_element is not None:
        return contact_element
    if group_element is not None:
        return group_element
    return None


def _is_control_row(entry: SearchEntry) -> bool:
    return not entry.identifier and (
        entry.text.startswith("View All")
        or entry.text.startswith("Collapse")
        or entry.text.startswith("查看全部")
        or entry.text.startswith("收起")
    )


def _summarize_search_candidates(
    entries: list[SearchEntry],
) -> dict[str, list[str]]:
    """
    Summarize candidate names from search entries, grouped by section.

    Returns up to 15 unique names from each of "Contacts" and
    "Group Chats"; all other sections are ignored.
    """
    headers = _build_section_headers(entries)
    contacts: list[str] = []
    group_chats: list[str] = []

    for entry in entries:
        if _is_section_header(entry) or _is_control_row(entry) or not entry.text:
            continue

        section = _classify_section(entry, headers)
        if section in SEARCH_SECTION_CONTACTS:
            if entry.text not in contacts:
                contacts.append(entry.text)
        elif section in SEARCH_SECTION_GROUPS:
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
        if not _is_control_row(entry) or entry.text.startswith(("Collapse", "收起")):
            continue
        section = _classify_section(entry, headers)
        if section == section_title:
            logger.info("Expanding %s section via %r", section_title, entry.text)
            click_element_center(entry.element)
            time.sleep(0.4)
            return


def _select_contact_from_search_results(
    ax_app, contact_name: str
) -> tuple[bool, dict[str, list[str]]]:
    """
    Try to open a chat by selecting an exact match from the global
    search results list, preferring Contacts over Group Chats and
    ignoring every other section.
    """
    search_list = wait_for_search_results(ax_app)
    if search_list is None:
        return False, {"contacts": [], "group_chats": []}

    aggregated_contacts: list[str] = []
    aggregated_groups: list[str] = []

    def update_candidates(entries: list[SearchEntry]) -> None:
        partial = _summarize_search_candidates(entries)
        for name in partial["contacts"]:
            if name not in aggregated_contacts:
                aggregated_contacts.append(name)
        for name in partial["group_chats"]:
            if name not in aggregated_groups:
                aggregated_groups.append(name)

    def candidates() -> dict[str, list[str]]:
        return {
            "contacts": aggregated_contacts[:15],
            "group_chats": aggregated_groups[:15],
        }

    # First, inspect the initial compact search popover without scrolling.
    entries = _collect_search_entries(search_list)
    update_candidates(entries)
    element = _find_exact_match_in_entries(entries, contact_name)
    if element is not None:
        logger.info("Found exact match for %s in initial search results", contact_name)
        click_element_center(element)
        return True, candidates()

    # No exact match visible yet; expand Contacts and Group Chats if possible.
    for title in (*SEARCH_SECTION_CONTACTS, *SEARCH_SECTION_GROUPS):
        _expand_section_if_needed(search_list, title)

    center = get_list_center(search_list)
    last_signature: tuple[str, ...] | None = None
    stable = 0

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
            return True, candidates()

        signature = tuple(e.text for e in entries)
        if not signature:
            break
        if signature == last_signature:
            stable += 1
            if stable >= 3:
                break
        else:
            last_signature = signature
            stable = 0

        # Negative delta scrolls downwards through the search results list.
        post_scroll(center, -30)
        time.sleep(0.15)

    return False, candidates()


def open_chat_for_contact(chat_name: str) -> dict[str, Any] | None:
    """
    Open a chat for a given name (contact or group).

    First, look for the chat in the left session list (scrolling through
    it if necessary). If it is not there, type the name into the global
    search field and pick an exact match, preferring "Contacts" over
    "Group Chats" and ignoring every other section.

    If no exact match can be found, this function does **not** fall back
    to the top search result. Instead, it returns a dict of the form:

    {
        "error": "<LLM-friendly message>",
        "chat_name": "<original chat_name>",
        "candidates": {
            "contacts": [... up to 15 names ...],
            "group_chats": [... up to 15 names ...],
        },
    }

    Callers can use this to ask the LLM to choose a more specific target.
    On success it returns None.
    """
    logger.info("Opening chat for name: %s", chat_name)
    ax_app = get_wechat_ax_app()
    close_search(ax_app)

    if chat_names_match(get_current_chat_name(ax_app), chat_name):
        logger.info("Chat %r is already open", chat_name)
        return None

    element = find_chat_element_by_name(ax_app, chat_name)
    if element is not None:
        logger.info("Found chat in session list, clicking it")
        click_element_center(element)
        time.sleep(0.5)
        opened = get_current_chat_name(ax_app)
        if chat_names_match(opened, chat_name):
            return None
        logger.warning(
            "Clicked session row for %r but current chat is %r; trying search",
            chat_name,
            opened,
        )

    logger.info("Chat not in session list, using global search")
    focus_and_type_search(ax_app, chat_name)

    try:
        found, candidates = _select_contact_from_search_results(ax_app, chat_name)
        if found:
            time.sleep(0.5)
            opened = get_current_chat_name(ax_app)
            if chat_names_match(opened, chat_name):
                logger.info("Opened chat for %s via search results", chat_name)
                return None
            close_search(ax_app)
            logger.error(
                "Search result click opened %r instead of %r; refusing to continue",
                opened,
                chat_name,
            )
            return {
                "error": (
                    "WeChat opened a different chat than requested "
                    f"({opened!r} instead of {chat_name!r}). Nothing was sent. "
                    "Check the exact chat name."
                ),
                "chat_name": chat_name,
                "opened_chat": opened,
                "candidates": candidates,
            }

        close_search(ax_app)
        error_msg = (
            "Could not find an exact match for the requested chat name in "
            "WeChat's Contacts or Group Chats search results. Returning "
            "related contact and group names so the LLM can choose a more "
            "specific chat to open."
        )
        logger.warning(
            "open_chat_for_contact(%s) returning candidates instead of "
            "opening a chat",
            chat_name,
        )
        return {
            "error": error_msg,
            "chat_name": chat_name,
            "candidates": candidates,
        }
    except Exception as exc:
        close_search(ax_app)
        logger.exception(
            "Error while selecting chat %s from search results: %s",
            chat_name,
            exc,
        )
        raise
