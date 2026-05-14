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
    kAXWindowRole,
)
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
    kCGEventMouseMoved,
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

    `activateWithOptions_` is asynchronous: macOS schedules the focus
    change but does not block until WeChat has actually finished
    repainting. WeChat 4.x's SwiftUI also defers populating the
    conversation `AXTable`'s `AXRows` until the window is fully drawn,
    which can take 200–800 ms after activation. Querying too soon
    yields an empty AX subtree and downstream callers see "0 chats".

    To stop callers from racing the OS we:

    1. Skip activation entirely if WeChat is already the frontmost app
       (most calls are made back-to-back from the same flow).
    2. After a real activation, briefly poll the AX tree until at least
       one window is reachable, capped at ~1 second.
    """
    bundle_id = "com.tencent.xinWeChat"
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        bundle_id
    )
    if not apps:
        raise RuntimeError("WeChat is not running")

    app = apps[0]
    pid = app.processIdentifier()
    ax_app = AXUIElementCreateApplication(pid)

    frontmost = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    already_front = (
        frontmost is not None
        and frontmost.bundleIdentifier() == bundle_id
        and bool(ax_get(ax_app, "AXWindows"))
    )
    if already_front:
        return ax_app

    app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
    logger.info(
        "Activated WeChat (bundle_id=%s, pid=%s)", bundle_id, pid
    )
    # Wait briefly for the AX tree to be populated. Poll in 50ms increments.
    deadline = time.time() + 1.0
    while time.time() < deadline:
        if ax_get(ax_app, "AXWindows"):
            break
        time.sleep(0.05)
    # Even with windows reachable, the SwiftUI table can lag a beat.
    time.sleep(0.15)
    return ax_app


def _find_window_by_title(ax_app: Any, title: str):
    """
    Locate a top-level WeChat window with the given title.
    """

    def is_window(el, role, current_title, identifier):
        return (
            role == kAXWindowRole
            and isinstance(current_title, str)
            and current_title == title
        )

    return dfs(ax_app, is_window)


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


# Localized labels for the section headers WeChat shows in the global
# search-results popover. Keys are canonical English names used internally;
# values list every locale variant we want to recognize. Add new locales
# here when WeChat ships them.
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "Contacts": ("Contacts", "联系人"),
    "Group Chats": ("Group Chats", "群聊"),
    "Chat History": ("Chat History", "聊天记录"),
    "Official Accounts": ("Official Accounts", "公众号"),
    "Internet search results": (
        "Internet search results",
        "联网搜索",
        "网络搜索结果",
    ),
    "More": ("More", "更多"),
}

# Reverse map: any locale variant -> canonical English name.
_SECTION_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}

# Locale variants of the "View All" expander row prefix.
VIEW_ALL_PREFIXES: tuple[str, ...] = ("View All", "查看全部", "查看更多")


def _canonical_section(text: str) -> str | None:
    """Return the canonical English section name for any locale variant."""
    if not isinstance(text, str):
        return None
    return _SECTION_ALIAS_TO_CANONICAL.get(text.strip())


def _is_view_all(text: str) -> bool:
    """Return True if `text` looks like a 'View All' expander row."""
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    return any(stripped.startswith(prefix) for prefix in VIEW_ALL_PREFIXES)


def _normalize_chat_title(name: str) -> str:
    """
    Normalize a WeChat chat title.

    In particular, strip a trailing "(<digits>)" suffix that WeChat
    appends for group chats to indicate member count, e.g.:
    "My Group(23)" -> "My Group".
    """
    name = name.strip()
    # Remove trailing "(number)" if present.
    name = re.sub(r"\(\d+\)$", "", name).strip()
    return name


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
        return _normalize_chat_title(value)

    title = ax_get(title_el, kAXTitleAttribute)
    if isinstance(title, str) and title.strip():
        return _normalize_chat_title(title)

    return None


def _parse_chat_name_from_4x_title(title: str) -> str | None:
    """
    WeChat 4.x SwiftUI exposes each visible chat as an AXRow whose AXTitle is
    a comma-joined summary like:
        "<chat name>,<last message preview>,<timestamp>[,<status>]"
    The AXIdentifier is just "MMChatsTableCellView_0" with no chat name.

    Take everything before the first ASCII comma (the convention WeChat uses
    to separate fields). This is a pragmatic compromise; it will misidentify
    chats whose display name contains an ASCII comma, but Chinese full-width
    "，" is left intact, and the user can always fall back to global search.
    """
    if not isinstance(title, str) or not title:
        return None
    name, _, _ = title.partition(",")
    name = name.strip()
    return name or None


def _find_inner_chats_cell_view(row, max_depth: int = 4) -> Any:
    """
    Inside a WeChat 4.x conversation-list AXTable, every selectable AXRow
    wraps an AXCell containing another AXRow whose AXIdentifier starts with
    "MMChatsTableCellView". The inner element is what carries the chat
    summary in its AXTitle. Return that inner element if found.
    """
    stack: list[tuple[Any, int]] = [(row, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > max_depth:
            continue
        identifier = ax_get(node, kAXIdentifierAttribute)
        if isinstance(identifier, str) and identifier.startswith(
            "MMChatsTableCellView"
        ):
            return node
        for child in ax_get(node, kAXChildrenAttribute) or []:
            stack.append((child, depth + 1))
    return None


def _find_chats_table(ax_app, retries: int = 8) -> Any:
    """
    Locate the AXTable that holds the WeChat 4.x conversation list. We
    identify it by looking for an AXTable whose subtree contains at least
    one descendant with `MMChatsTableCellView*` identifier.

    Retries a few times with short sleeps because immediately after WeChat
    is activated (especially from a hidden state) the SwiftUI table
    sometimes appears in the AX tree before its rows are populated. Cold
    starts on macOS 14+/Apple Silicon have been observed to need ~2-3
    seconds before the conversation list is queryable. We retry in 0.4 s
    increments up to ~3 s total, but only sleep when the first probe
    misses, so warm calls remain instant.
    """
    for attempt in range(max(1, retries)):
        found: list[Any] = []

        def walk(element, depth: int = 0) -> None:
            if depth > 16 or found:
                return
            if ax_get(element, kAXRoleAttribute) == "AXTable":
                if _find_inner_chats_cell_view(element, max_depth=4) is not None:
                    found.append(element)
                    return
            for child in ax_get(element, kAXChildrenAttribute) or []:
                walk(child, depth + 1)

        walk(ax_app, 0)
        if found:
            return found[0]
        if attempt < retries - 1:
            time.sleep(0.4)
    return None


# Module-level cache of (chat_name -> wrapper_row) so that
# `select_chat_in_table_4x` can find the table once `find_chat_element_by_name`
# has returned the wrapper row.
_CHATS_TABLE_BY_PID: dict[int, Any] = {}


def collect_chat_elements(ax_app) -> dict[str, Any]:
    """
    Collect chat elements from the left session list keyed by display name.

    Supports two AX layouts:
      - WeChat 3.x (legacy): each session item is an AXStaticText whose
        AXIdentifier is "session_item_<chat_name>".
      - WeChat 4.x (SwiftUI rewrite): each session item is wrapped in an
        AXRow > AXCell > AXRow tree, where the inner AXRow has identifier
        "MMChatsTableCellView*" and AXTitle "<chat_name>,<preview>,...".

    For 4.x we enumerate every row of the conversation AXTable, not just
    those currently rendered. The SwiftUI table virtualizes drawing (only a
    handful of rows are physically painted at a time) but it exposes every
    user history row in `AXRows` and accepts `AXSelectedRows` writes against
    *any* of them. Returning every row therefore lets `open_chat_for_contact`
    reach any chat in the user's history without scrolling the sidebar or
    going through the global-search popover, both of which are fragile.

    The mapping value for 4.x is the *outer wrapper* AXRow (the one the
    parent AXTable considers a "row"). CGEvent clicks on these rows are
    unreliable on macOS 14+; setting the table's selection is the supported
    and idempotent path.
    """
    results: dict[str, Any] = {}

    # 1) WeChat 4.x layout via the conversation AXTable.
    table = _find_chats_table(ax_app)
    if table is not None:
        try:
            _CHATS_TABLE_BY_PID[id(ax_app)] = table
        except Exception:
            pass

        # Prefer AXRows (every row, including virtual off-screen ones) over
        # AXVisibleRows. WeChat's SwiftUI table populates AXRows with the
        # full session history — typically ~1 row per chat the user has
        # ever messaged, so a few hundred entries on busy accounts.
        wrappers = ax_get(table, "AXRows") or ax_get(table, kAXChildrenAttribute) or []
        for wrapper in wrappers:
            inner = _find_inner_chats_cell_view(wrapper)
            if inner is None:
                continue
            chat_name = _parse_chat_name_from_4x_title(
                ax_get(inner, kAXTitleAttribute)
            )
            if chat_name and chat_name not in results:
                results[chat_name] = wrapper

        if results:
            logger.info(
                "Collected %d chat elements (WeChat 4.x via AXRows)",
                len(results),
            )
            return results

    # 2) Legacy 3.x layout.
    def walk(element):
        role = ax_get(element, kAXRoleAttribute)
        identifier = ax_get(element, kAXIdentifierAttribute)
        if isinstance(role, str) and isinstance(identifier, str):
            if role == kAXStaticTextRole and identifier.startswith("session_item_"):
                chat_name = identifier[len("session_item_") :]
                if chat_name:
                    results[chat_name] = element
        for child in ax_get(element, kAXChildrenAttribute) or []:
            walk(child)

    walk(ax_app)
    logger.info("Collected %d chat elements from session list", len(results))
    return results


def select_chat_in_table_4x(wrapper_row) -> bool:
    """
    Open the chat backed by `wrapper_row` by setting it as the selection on
    its parent AXTable. Returns True on success.

    This is the WeChat 4.x preferred path because the SwiftUI table swallows
    most CGEvent left-clicks at the system level. AXSelectedRows is observed
    by the SwiftUI binding layer and reliably triggers chat navigation.
    """
    if wrapper_row is None:
        return False
    # Walk up through AXParent until we hit the enclosing AXTable.
    table = None
    cursor = wrapper_row
    for _ in range(8):
        parent = ax_get(cursor, "AXParent")
        if parent is None:
            break
        if ax_get(parent, kAXRoleAttribute) == "AXTable":
            table = parent
            break
        cursor = parent
    if table is None:
        return False
    err = AXUIElementSetAttributeValue(table, "AXSelectedRows", [wrapper_row])
    return err == 0


def find_chat_element_by_name(ax_app, chat_name: str):
    """
    Find a chat element whose name matches the given chat name exactly
    (case-sensitive and case-insensitive match are both attempted).
    """
    chat_elements = collect_chat_elements(ax_app)
    if chat_name in chat_elements:
        return chat_elements[chat_name]

    lowered = {name.lower(): el for name, el in chat_elements.items()}
    match = lowered.get(chat_name.lower())
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
    Activate `element` — by setting AXSelectedRows on the enclosing AXTable
    if the element is a 4.x conversation-list wrapper row, otherwise by
    synthesizing a real left mouse click at its visual center.

    WeChat 4.x's session-list rows expose only AXShowMenu (right-click) as a
    supported AX action, and the SwiftUI table consumes most CGEvent clicks
    at the OS level, so for those rows we drive selection via the parent
    table's AXSelectedRows attribute. This is also significantly more robust
    than mouse simulation because it does not require WeChat to be
    frontmost / unobscured.

    For all other elements we fall back to a real mouse click. Some
    SwiftUI hit-testing requires a hover before the mouseDown and a small
    delay between down and up before the click registers, so the synthetic
    sequence is move → down → (delay) → up rather than back-to-back events.
    """
    # 4.x wrapper-row fast path
    if select_chat_in_table_4x(element):
        return

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
    pt = CGPoint(cx, cy)

    event_move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, pt, 0)
    CGEventPost(kCGHIDEventTap, event_move)
    time.sleep(0.05)
    event_down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, pt, 0)
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(0.08)
    event_up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, pt, 0)
    CGEventPost(kCGHIDEventTap, event_up)


def long_press_element_center(element, hold_seconds: float = 2.2) -> None:
    """
    Synthesize a long left mouse press at the visual center of the
    given element.
    """
    pos_ref = ax_get(element, kAXPositionAttribute)
    size_ref = ax_get(element, kAXSizeAttribute)
    point = axvalue_to_point(pos_ref)
    size = axvalue_to_size(size_ref)
    if point is None or size is None:
        raise RuntimeError("Failed to get bounds for element to long-press")

    x, y = point
    w, h = size
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


def find_search_field(ax_app):
    """
    Locate the sidebar search input.

    WeChat exposes this differently across versions:
      - 3.x: AXTextArea with AXTitle == "Search" (English-only build).
      - 4.x: AXTextField with no useful title/identifier; it lives at the top
        of the left split-group and has no AXValue when empty.

    Returns the first matching element. We prefer the legacy match because
    it is unambiguous; otherwise we fall back to the topmost shallow
    AXTextField inside any AXSplitGroup.
    """

    def is_legacy_search(el, role, title, identifier):
        return role == kAXTextAreaRole and title == "Search"

    legacy = dfs(ax_app, is_legacy_search)
    if legacy is not None:
        return legacy

    # 4.x fallback: collect all shallow AXTextFields with no value and pick
    # the one with the smallest Y position.
    candidates: list[tuple[float, Any]] = []

    def walk(element, depth: int) -> None:
        if depth > 6:
            return
        role = ax_get(element, kAXRoleAttribute)
        if isinstance(role, str) and role == "AXTextField":
            value = ax_get(element, kAXValueAttribute)
            # Search field is empty by default; chat input may also be empty.
            # Use Y position to disambiguate (search is at top of sidebar).
            pos_ref = ax_get(element, kAXPositionAttribute)
            point = axvalue_to_point(pos_ref)
            y = point[1] if point is not None else float("inf")
            if not value:
                candidates.append((float(y), element))
        children = ax_get(element, kAXChildrenAttribute) or []
        for child in children:
            walk(child, depth + 1)

    walk(ax_app, 0)

    if not candidates:
        raise RuntimeError(
            "Could not find WeChat search text field via Accessibility API"
        )
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]


def focus_and_type_search(ax_app, text: str):
    """
    Focus the WeChat sidebar search field and type the given text using
    Command+A and Command+V
    """
    search = find_search_field(ax_app)

    AXUIElementPerformAction(search, kAXRaiseAction)

    # Clear any existing value via AX (best effort).
    err = AXUIElementSetAttributeValue(search, kAXValueAttribute, "")
    if err != 0:
        logger.debug("Failed to clear search field via AX (err=%s)", err)

    pb = AppKit.NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, AppKit.NSPasteboardTypeString)

    time.sleep(0.1)

    keycode_a = 0  # US keyboard 'A'
    keycode_v = 9  # US keyboard 'V'
    send_key_with_modifiers(keycode_a, kCGEventFlagMaskCommand)
    time.sleep(0.05)
    send_key_with_modifiers(keycode_v, kCGEventFlagMaskCommand)


def open_chat_for_contact(chat_name: str) -> dict[str, Any] | None:
    """
    Open a chat for a given name (contact or group).

    First, search in the left sidebar session list. If found, click it.
    If not, type the name into the global search field and inspect the
    search results:
    - Prefer an exact match under the "Contacts" section.
    - Otherwise, prefer an exact match under the "Group Chats" section.
    - If no exact match is visible, expand "View All" for Contacts and
      Group Chats (if present) and scroll through results, looking for
      an exact match while explicitly ignoring the "Chat History", "Official Accounts", "Internet search results", and "More" sections.

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
    """
    logger.info("Opening chat for name: %s", chat_name)
    ax_app = get_wechat_ax_app()

    element = find_chat_element_by_name(ax_app, chat_name)
    if element is not None:
        logger.info("Found chat in session list, clicking center")
        click_element_center(element)
        time.sleep(0.3)
        return

    logger.info("Chat not in session list, using global search")
    focus_and_type_search(ax_app, chat_name)
    time.sleep(0.4)

    try:
        found, candidates = _select_contact_from_search_results(ax_app, chat_name)
        if found:
            logger.info("Opened chat for %s via search results", chat_name)
            time.sleep(0.4)
            return None

        logger.info(
            "Exact match for %s not found in Contacts/Group Chats search "
            "results; returning candidate names",
            chat_name,
        )
        error_msg = (
            "Could not find an exact match for the requested chat name in "
            "WeChat's Contacts or Group Chats search results. Returning "
            "related contact and group names so the LLM can choose a more "
            "specific chat to open."
        )
        logger.warning(
            "open_chat_for_contact(%s) returning candidates instead of "
            "opening a chat: %s",
            chat_name,
            error_msg,
        )
        return {
            "error": error_msg,
            "chat_name": chat_name,
            "candidates": candidates,
        }
    except Exception as exc:
        logger.exception(
            "Error while selecting chat %s from search results: %s",
            chat_name,
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
    Map known section titles to their vertical Y coordinate within the search
    list. Locale variants are normalized to canonical English names via
    `SECTION_ALIASES`, so downstream code can keep working with the English
    keys regardless of WeChat's interface language.
    """
    headers: dict[str, float] = {}
    for entry in entries:
        canonical = _canonical_section(entry.text)
        if canonical is not None and canonical not in headers:
            headers[canonical] = entry.y
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


def _find_exact_match_in_entries(entries: list[SearchEntry], contact_name: str):
    """
    Look for an exact match in the current snapshot of search results.

    Preference order:
    - Exact match under "Contacts"
    - Exact match under "Group Chats"

    Entries classified as "Chat History", "Official Accounts", "Internet search results", or "More" are ignored.
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

    Entries belonging to "Chat History", "Official Accounts", "Internet search results", or "More" are ignored.
    """
    headers = _build_section_headers(entries)
    contacts: list[str] = []
    group_chats: list[str] = []

    for entry in entries:
        # Skip section headers themselves (any locale).
        if _canonical_section(entry.text) is not None:
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
        if not _is_view_all(entry.text):
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
    ignoring the Chat History, Official Accounts, "Internet search results", and More sections.
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
        logger.info("Found exact match for %s in initial search results", contact_name)
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
            txt = ax_get(child, kAXValueAttribute) or ax_get(child, kAXTitleAttribute)
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

        # Negative delta scrolls downwards through the search results list.
        post_scroll(center, -80)
        time.sleep(0.1)

    return False, {
        "contacts": list(aggregated_contacts)[:15],
        "group_chats": list(aggregated_groups)[:15],
    }


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


def get_list_center(msg_list):
    """
    Compute the on-screen center point of the messages (or search) list,
    used as the target for scroll-wheel events.
    """
    pos_ref = ax_get(msg_list, kAXPositionAttribute)
    size_ref = ax_get(msg_list, kAXSizeAttribute)
    origin = axvalue_to_point(pos_ref)
    size = axvalue_to_size(size_ref)
    if origin is None or size is None:
        raise RuntimeError("Failed to get bounds for list element")

    x, y = origin
    w, h = size
    return x + w / 2.0, y + h / 2.0


def post_scroll(center, delta_lines: int) -> None:
    """
    Post a scroll-wheel event at the given screen position.

    On a standard macOS configuration:
    - Positive delta_lines scrolls towards older content (upwards in history).
    - Negative delta_lines scrolls towards newer content (downwards in history).
    """
    cx, cy = center
    event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, delta_lines)
    CGEventSetLocation(event, CGPoint(cx, cy))
    CGEventPost(kCGHIDEventTap, event)
