from __future__ import annotations

import time
from typing import Any

from ApplicationServices import (
    kAXButtonRole,
    kAXChildrenAttribute,
    kAXIdentifierAttribute,
    kAXTextAreaRole,
    kAXValueAttribute,
)

from .logging_config import logger
from .wechat_accessibility import (
    ID_CHAT_INPUT,
    ax_get,
    chat_names_match,
    get_current_chat_name,
    click_element_center,
    dfs,
    element_text,
    ensure_chats_tab,
    find_by_identifier,
    get_wechat_ax_app,
    press_return,
    set_text_value,
)

SEND_BUTTON_TITLES = ("Send", "发送")


def find_input_field(ax_app: Any):
    """
    Locate the chat input text area in the main WeChat window.
    """
    main_window = ensure_chats_tab(ax_app)
    input_field = find_by_identifier(main_window, ID_CHAT_INPUT, kAXTextAreaRole)
    if input_field is None:
        raise RuntimeError(
            "Could not find WeChat chat input field via Accessibility API"
        )
    return input_field


def _find_send_button(ax_app: Any):
    main_window = ensure_chats_tab(ax_app)

    def is_send(el, role, title, identifier):
        return role == kAXButtonRole and title in SEND_BUTTON_TITLES

    return dfs(main_window, is_send)


def _wait_until_input_empty(input_field: Any, timeout: float) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        value = ax_get(input_field, kAXValueAttribute)
        if not value:
            return True
        time.sleep(0.1)
    return False


def _last_bubble_text(ax_app: Any) -> str | None:
    main_window = ensure_chats_tab(ax_app)
    msg_list = find_by_identifier(main_window, "chat_message_list")
    if msg_list is None:
        return None
    last = None
    for child in ax_get(msg_list, kAXChildrenAttribute) or []:
        if ax_get(child, kAXIdentifierAttribute) == "chat_bubble_item_view":
            text = element_text(child)
            if text:
                last = text
    return last


def _verify_sent(ax_app: Any, text: str) -> dict[str, Any]:
    time.sleep(0.4)
    last = _last_bubble_text(ax_app)
    verified = last is not None and last.strip() == text.strip()
    if not verified:
        logger.warning("Could not verify sent message; last bubble is %r", last)
    return {"sent": True, "verified": verified, "last_bubble": last}


def send_message(text: str, expected_chat: str | None = None) -> dict[str, Any]:
    """
    Send a message in the currently open chat by setting the input
    field's value and pressing Return (falling back to the Send button).

    When ``expected_chat`` is given the send is refused unless that chat
    is the one currently open. Returns a dict with ``sent`` and
    ``verified`` (whether the newest bubble now shows the text).
    """
    logger.info("Sending message of length %d characters", len(text))
    ax_app = get_wechat_ax_app()
    if expected_chat is not None:
        current = get_current_chat_name(ax_app)
        if not chat_names_match(current, expected_chat):
            raise RuntimeError(
                f"Refusing to send: the open chat is {current!r}, not {expected_chat!r}"
            )
    input_field = find_input_field(ax_app)

    if not set_text_value(input_field, text):
        raise RuntimeError("Failed to put the message into the WeChat input field")

    time.sleep(0.15)
    press_return()
    if _wait_until_input_empty(input_field, timeout=1.5):
        logger.info("Message sent via Return")
        return _verify_sent(ax_app, text)

    # Return may be configured to insert a newline; use the Send button.
    logger.info("Input still has content after Return; clicking Send button")
    send_button = _find_send_button(ax_app)
    if send_button is None:
        raise RuntimeError("Message was not sent and no Send button was found")
    click_element_center(send_button)
    if _wait_until_input_empty(input_field, timeout=2.0):
        logger.info("Message sent via Send button")
        return _verify_sent(ax_app, text)

    raise RuntimeError(
        "Message was not sent: the input field still contains text "
        f"(last bubble: {_last_bubble_text(ax_app)!r})"
    )
