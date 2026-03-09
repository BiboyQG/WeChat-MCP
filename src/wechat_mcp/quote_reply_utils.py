"""
Utilities for quoting and replying to a specific message in WeChat.

This module provides the ability to right-click on a message in the
currently open chat, select "Quote" from the context menu, and then
type and send a reply with the quoted message attached.
"""

from __future__ import annotations

import time
from typing import Any

from ApplicationServices import (
    AXUIElementCopyAttributeValue,
    kAXChildrenAttribute,
    kAXRoleAttribute,
    kAXTitleAttribute,
    kAXValueAttribute,
)
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    CGPoint,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGHIDEventTap,
)

from .logging_config import logger
from .wechat_accessibility import (
    ax_get,
    axvalue_to_point,
    axvalue_to_size,
    click_element_center,
    dfs,
    get_wechat_ax_app,
    kAXPositionAttribute,
    kAXSizeAttribute,
)
from .fetch_messages_by_chat_utils import get_messages_list
from .reply_to_messages_by_chat_utils import find_input_field, press_return, send_message


def right_click_element_center(element) -> None:
    """
    Synthesize a right mouse click at the visual center of the given
    AX element, which opens the context menu in WeChat.
    """
    pos_ref = ax_get(element, kAXPositionAttribute)
    size_ref = ax_get(element, kAXSizeAttribute)
    point = axvalue_to_point(pos_ref)
    size = axvalue_to_size(size_ref)
    if point is None or size is None:
        raise RuntimeError("Failed to get bounds for element to right-click")
    x, y = point
    w, h = size
    cx = x + w / 2.0
    cy = y + h / 2.0
    event_down = CGEventCreateMouseEvent(
        None, kCGEventRightMouseDown, CGPoint(cx, cy), 0
    )
    event_up = CGEventCreateMouseEvent(
        None, kCGEventRightMouseUp, CGPoint(cx, cy), 0
    )
    CGEventPost(kCGHIDEventTap, event_down)
    time.sleep(0.05)
    CGEventPost(kCGHIDEventTap, event_up)


def find_context_menu_item(ax_app, item_title: str, timeout: float = 3.0):
    """
    Wait for a context menu to appear and find a menu item by title.

    WeChat's context menu items (Copy, Quote, Forward, etc.) are
    standard AX menu items that can be located via DFS.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        def is_menu_item(el, role, title, identifier):
            return (
                role == "AXMenuItem"
                and title is not None
                and item_title.lower() in str(title).lower()
            )

        found = dfs(ax_app, is_menu_item)
        if found is not None:
            return found
        time.sleep(0.1)
    return None


def find_message_element(msg_list, target_text: str):
    """
    Find a message element in the message list whose text content
    contains the target text.

    Returns the AX element for the matching message, or None.
    """
    children = ax_get(msg_list, kAXChildrenAttribute) or []
    best_match = None
    best_len = float("inf")
    for child in children:
        text = ax_get(child, kAXValueAttribute) or ax_get(child, kAXTitleAttribute)
        if text and target_text in str(text):
            # Prefer the shortest match to avoid matching overly broad elements
            if len(str(text)) < best_len:
                best_match = child
                best_len = len(str(text))
    return best_match


def dismiss_context_menu(ax_app) -> None:
    """
    Press Escape to dismiss any open context menu.
    """
    from Quartz import CGEventCreateKeyboardEvent, CGEventSetFlags

    keycode_escape = 53
    event_down = CGEventCreateKeyboardEvent(None, keycode_escape, True)
    CGEventSetFlags(event_down, 0)
    event_up = CGEventCreateKeyboardEvent(None, keycode_escape, False)
    CGEventSetFlags(event_up, 0)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


def quote_and_reply(target_text: str, reply_text: str) -> dict[str, Any]:
    """
    Quote a specific message and send a reply.

    Steps:
    1. Find the message element containing `target_text` in the
       currently open chat's message list.
    2. Right-click on that message to open the context menu.
    3. Click the "Quote" menu item.
    4. Type the reply text into the input field and send.

    Args:
        target_text: A substring of the message to quote. Must be
            unique enough to identify the correct message.
        reply_text: The reply text to send along with the quote.

    Returns:
        A dict with keys ``quoted_text``, ``reply_text``, and ``sent``.
    """
    ax_app = get_wechat_ax_app()
    msg_list = get_messages_list(ax_app)

    # Step 1: Find the target message
    msg_element = find_message_element(msg_list, target_text)
    if msg_element is None:
        raise RuntimeError(
            f"Could not find a message containing: {target_text!r}"
        )
    logger.info("Found message element for quote target: %r", target_text)

    # Step 2: Right-click to open context menu
    right_click_element_center(msg_element)
    time.sleep(0.5)

    # Step 3: Find and click "Quote" in the context menu
    quote_item = find_context_menu_item(ax_app, "Quote")
    if quote_item is None:
        # Try Chinese label as fallback
        quote_item = find_context_menu_item(ax_app, "引用")
    if quote_item is None:
        dismiss_context_menu(ax_app)
        raise RuntimeError(
            "Could not find 'Quote' item in the context menu"
        )
    click_element_center(quote_item)
    logger.info("Clicked 'Quote' in context menu")
    time.sleep(0.3)

    # Step 4: Type reply and send
    send_message(reply_text)
    logger.info("Quote-reply sent: quoted=%r, reply=%r", target_text, reply_text)

    return {
        "quoted_text": target_text,
        "reply_text": reply_text,
        "sent": True,
    }

