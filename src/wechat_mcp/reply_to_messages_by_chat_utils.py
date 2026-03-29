from __future__ import annotations

import time
from typing import Any

from ApplicationServices import (
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    kAXRaiseAction,
    kAXTextAreaRole,
    kAXValueAttribute,
)
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPostToPid,
    CGEventSetFlags,
)

from .logging_config import logger
from .wechat_accessibility import dfs, get_wechat_ax_app, get_wechat_pid


def press_return(pid: int) -> None:
    """
    Synthesize a Return key press directed at the given process PID.
    """
    keycode_return = 36
    event_down = CGEventCreateKeyboardEvent(None, keycode_return, True)
    CGEventSetFlags(event_down, 0)
    event_up = CGEventCreateKeyboardEvent(None, keycode_return, False)
    CGEventSetFlags(event_up, 0)
    CGEventPostToPid(pid, event_down)
    CGEventPostToPid(pid, event_up)


def find_input_field(ax_app: Any):
    """
    Locate the chat input text area in the current WeChat window.
    """

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
    pid = get_wechat_pid()
    press_return(pid)
    logger.info("Message sent")
