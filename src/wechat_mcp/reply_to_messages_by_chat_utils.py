from __future__ import annotations

import time
from typing import Any

import AppKit
from ApplicationServices import (
    AXUIElementCopyAttributeValue,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    kAXRaiseAction,
    kAXTextAreaRole,
    kAXValueAttribute,
)
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)

from .logging_config import logger
from .wechat_accessibility import ax_get, dfs, get_wechat_ax_app


def press_return() -> None:
    """
    Synthesize a Return key press.
    """
    keycode_return = 36
    event_down = CGEventCreateKeyboardEvent(None, keycode_return, True)
    CGEventSetFlags(event_down, 0)
    event_up = CGEventCreateKeyboardEvent(None, keycode_return, False)
    CGEventSetFlags(event_up, 0)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


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


def send_key_with_modifiers(keycode: int, flags: int):
    """
    Send a keyboard event with modifiers (e.g., Cmd+V).
    """
    event_down = CGEventCreateKeyboardEvent(None, keycode, True)
    CGEventSetFlags(event_down, flags)
    event_up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(event_up, flags)
    CGEventPost(kCGHIDEventTap, event_down)
    CGEventPost(kCGHIDEventTap, event_up)


def send_message(text: str) -> None:
    """
    Send a message in the currently open chat by focusing the input
    field, setting its value, and pressing Return.

    Uses two methods with fallback:
    1. Try to set value directly via Accessibility API
    2. If that fails, use keyboard simulation via pasteboard (Cmd+V)
    """
    logger.info("Sending message of length %d characters", len(text))
    ax_app = get_wechat_ax_app()
    input_field = find_input_field(ax_app)

    # Focus the input field
    AXUIElementPerformAction(input_field, kAXRaiseAction)
    time.sleep(0.1)

    # Method 1: Try to set value directly via Accessibility API
    err = AXUIElementSetAttributeValue(input_field, kAXValueAttribute, text)

    # Verify the text was actually set by reading it back
    time.sleep(0.05)
    actual_value = ax_get(input_field, kAXValueAttribute)

    if err == 0 and actual_value == text:
        logger.debug("Successfully set message text via Accessibility API")
    else:
        # Method 2: Fallback to keyboard simulation via pasteboard
        logger.warning(
            "Accessibility API failed to set text (err=%s, actual=%r vs expected=%r), "
            "falling back to keyboard simulation",
            err,
            actual_value,
            text,
        )

        # Clear the field first (Cmd+A to select all)
        keycode_a = 0  # US keyboard 'A'
        send_key_with_modifiers(keycode_a, kCGEventFlagMaskCommand)
        time.sleep(0.05)

        # Copy text to pasteboard
        pb = AppKit.NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, AppKit.NSPasteboardTypeString)
        time.sleep(0.05)

        # Paste (Cmd+V)
        keycode_v = 9  # US keyboard 'V'
        send_key_with_modifiers(keycode_v, kCGEventFlagMaskCommand)
        time.sleep(0.1)

        # Verify again
        actual_value = ax_get(input_field, kAXValueAttribute)
        if actual_value != text:
            logger.error(
                "Failed to set message text even with keyboard simulation. "
                "Expected %r, got %r",
                text,
                actual_value,
            )
            raise RuntimeError(
                f"Failed to set input text. Expected {text!r}, got {actual_value!r}"
            )

        logger.info("Successfully set message text via keyboard simulation")

    # Send the message
    time.sleep(0.1)
    press_return()
    time.sleep(0.2)

    # Final verification: check if the input field is now empty (message was sent)
    final_value = ax_get(input_field, kAXValueAttribute)
    if final_value and final_value.strip():
        logger.warning(
            "Input field still contains text after pressing Return: %r. "
            "Message may not have been sent.",
            final_value,
        )
        raise RuntimeError(
            f"Message may not have been sent. Input field still contains: {final_value!r}"
        )

    logger.info("Message sent successfully")
