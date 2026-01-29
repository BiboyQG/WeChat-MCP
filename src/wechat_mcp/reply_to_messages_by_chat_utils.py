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
from .wechat_accessibility import (
    ax_get,
    dfs,
    get_wechat_ax_app,
    send_key_with_modifiers,
)

# ANSI keyboard keycodes (US layout)
KEYCODE_ANSI_A = 0
KEYCODE_ANSI_V = 9
KEYCODE_RETURN = 36


def press_return() -> None:
    """
    Synthesize a Return key press.
    """
    event_down = CGEventCreateKeyboardEvent(None, KEYCODE_RETURN, True)
    CGEventSetFlags(event_down, 0)
    event_up = CGEventCreateKeyboardEvent(None, KEYCODE_RETURN, False)
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
        send_key_with_modifiers(KEYCODE_ANSI_A, kCGEventFlagMaskCommand)
        time.sleep(0.05)

        # Copy text to pasteboard, while preserving user's clipboard
        pb = AppKit.NSPasteboard.generalPasteboard()
        saved_items = pb.pasteboardItems()
        try:
            pb.clearContents()
            pb.setString_forType_(text, AppKit.NSPasteboardTypeString)
            time.sleep(0.05)

            # Paste (Cmd+V)
            send_key_with_modifiers(KEYCODE_ANSI_V, kCGEventFlagMaskCommand)
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
        finally:
            # Restore original pasteboard content
            pb.clearContents()
            if saved_items:
                pb.writeObjects_(saved_items)

    # Send the message with retry logic to handle concurrent user interaction
    max_retries = 5
    for attempt in range(max_retries):
        # Re-focus the input field before each attempt to ensure it has focus
        AXUIElementPerformAction(input_field, kAXRaiseAction)
        time.sleep(0.15)

        # Press Return to send
        press_return()

        # Wait for input field to clear, with a timeout (polling approach)
        timeout = time.time() + 1.0  # 1 second timeout
        final_value = None
        while time.time() < timeout:
            final_value = ax_get(input_field, kAXValueAttribute)
            if not final_value or not final_value.strip():
                logger.info("Message sent successfully")
                return
            time.sleep(0.1)

        # Message not sent yet, log and retry
        logger.warning(
            "Attempt %d/%d: Input field still contains text after pressing Return: %r. "
            "Retrying...",
            attempt + 1,
            max_retries,
            final_value,
        )

        # If this wasn't the last attempt, wait a bit before retrying
        if attempt < max_retries - 1:
            time.sleep(0.2)

    # All retries failed
    logger.error(
        "Failed to send message after %d attempts. Input field still contains: %r",
        max_retries,
        final_value,
    )
    raise RuntimeError(
        f"Message may not have been sent after {max_retries} attempts. "
        f"Input field still contains: {final_value!r}"
    )
