from __future__ import annotations

import argparse
import logging
import os
import threading
from contextlib import contextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from .add_contact_by_wechat_id_utils import (
    add_contact_by_wechat_id as ax_add_contact_by_wechat_id,
)
from .compat import (
    compatibility_report,
    failure_context,
    get_version_info,
    version_warnings,
)
from .fetch_messages_by_chat_utils import ChatMessage, fetch_recent_messages
from .logging_config import logger
from .publish_moment_utils import publish_moment_without_media as ax_publish_moment
from .reply_to_messages_by_chat_utils import send_message
from .wechat_accessibility import (
    WECHAT_BUNDLE_ID,
    activate_bundle,
    chat_names_match,
    get_current_chat_name,
    get_frontmost_bundle_id,
    get_mouse_location,
    get_wechat_ax_app,
    list_session_chats,
    move_mouse,
    open_chat_for_contact,
)


mcp = FastMCP("WeChat Helper MCP Server")

# WeChat can only be driven by one automation at a time.
_ui_lock = threading.RLock()

ENV_RESTORE_FOCUS = "WECHAT_MCP_RESTORE_FOCUS"


def _restore_focus_enabled() -> bool:
    return os.getenv(ENV_RESTORE_FOCUS, "1").strip().lower() not in ("0", "false", "no")


@contextmanager
def ui_session():
    """
    Serialise WeChat automation and, once the tool is done, give the
    foreground back to whatever application the user was using.
    """
    with _ui_lock:
        previous = get_frontmost_bundle_id()
        pointer = get_mouse_location()
        try:
            yield
        finally:
            if _restore_focus_enabled():
                try:
                    move_mouse(*pointer)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Could not restore pointer: %s", exc)
            if (
                _restore_focus_enabled()
                and previous
                and previous != WECHAT_BUNDLE_ID
                and get_frontmost_bundle_id() == WECHAT_BUNDLE_ID
            ):
                if activate_bundle(previous):
                    logger.info("Restored focus to %s", previous)


def _with_warnings(result: dict[str, Any]) -> dict[str, Any]:
    warnings = version_warnings()
    if warnings:
        result.setdefault("warnings", []).extend(warnings)
    return result


def _error_result(exc: Exception, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"error": str(exc), **extra}
    try:
        result["diagnostics"] = failure_context(exc)
    except Exception as diag_exc:  # noqa: BLE001
        logger.debug("Could not build failure diagnostics: %s", diag_exc)
    return result


def _open_target_chat(chat_name: str, tool: str) -> dict[str, Any] | None:
    """
    Make sure ``chat_name`` is the open chat. Returns None on success or an
    error dict (candidates / mismatch) that the tool should return as is.
    """
    current_chat = get_current_chat_name()
    same_chat = chat_names_match(current_chat, chat_name)
    logger.info(
        "Current chat title=%r, target=%r, same_chat=%s",
        current_chat,
        chat_name,
        same_chat,
    )
    if same_chat:
        return None
    open_result = open_chat_for_contact(chat_name)
    if isinstance(open_result, dict) and open_result.get("error"):
        enriched = dict(open_result)
        enriched.setdefault("tool", tool)
        return enriched
    return None


@mcp.tool()
def fetch_messages_by_chat(
    chat_name: str,
    last_n: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch recent messages for a specific chat (contact or group).

    This will:
    - Look for the chat in the left sidebar session list (scrolling it)
    - If not found, search for the chat via the search box
    - Once the chat is open, retrieve the last ``last_n`` rows

    Each row has:
    - ``sender``: "ME", "OTHER", "SYSTEM" (timestamps / notices) or "UNKNOWN"
    - ``sender_name``: contact name for 1:1 chats, OCR'd member name in
      group chats (None for your own messages or when unreadable)
    - ``kind``: text, image, file, video, sticker, voice, link, card, system
    - ``text``: the message text (file rows: "File\\n<name>\\n<size>\\n...")

    If the chat name is ambiguous the single returned row carries an
    ``error`` and ``candidates`` from WeChat's search.
    """
    try:
        with ui_session():
            logger.info("Tool fetch_messages_by_chat called for chat=%s", chat_name)
            problem = _open_target_chat(chat_name, "fetch_messages_by_chat")
            if problem is not None:
                return [_with_warnings(problem)]

            messages: list[ChatMessage] = fetch_recent_messages(last_n=last_n)
            result = [msg.to_dict() for msg in messages]
            logger.info("Returning %d messages for chat=%s", len(result), chat_name)
            warnings = version_warnings()
            if warnings:
                result.insert(0, {"warnings": warnings})
            return result
    except Exception as exc:
        logger.exception("Error in fetch_messages_by_chat for chat=%s: %s", chat_name, exc)
        return [_error_result(exc, chat_name=chat_name)]


@mcp.tool()
def reply_to_messages_by_chat(
    chat_name: str,
    reply_message: str | None = None,
) -> dict[str, Any]:
    """
    Optionally send a reply to a chat (contact or group).

    This tool is designed to be driven by the LLM using this MCP:
    - Call fetch_messages_by_chat first to inspect conversation history.
    - Have the LLM compose a reply string.
    - Call this tool with that reply string to send it.

    The message is only sent when the chat that is open in WeChat matches
    ``chat_name`` exactly; otherwise nothing is sent and the result
    explains why. ``verified`` tells whether the newest bubble shows the
    sent text. If reply_message is None or empty, no message is sent; the
    tool still ensures the chat is open.
    """
    logger.info(
        "Tool reply_to_messages_by_chat called for chat=%s (has_reply=%s)",
        chat_name,
        bool(reply_message),
    )
    try:
        with ui_session():
            problem = _open_target_chat(chat_name, "reply_to_messages_by_chat")
            if problem is not None:
                problem.update({"reply_message": reply_message, "sent": False})
                return _with_warnings(problem)

            result: dict[str, Any] = {
                "chat_name": chat_name,
                "reply_message": reply_message,
                "sent": False,
            }
            if reply_message is not None and reply_message.strip():
                outcome = send_message(reply_message, expected_chat=chat_name)
                result.update(outcome)
                logger.info(
                    "Reply sent to chat=%s; message length=%d; verified=%s",
                    chat_name,
                    len(reply_message),
                    outcome.get("verified"),
                )
            return _with_warnings(result)
    except Exception as exc:
        logger.exception("Error in reply_to_messages_by_chat for chat=%s: %s", chat_name, exc)
        return _error_result(exc, chat_name=chat_name, sent=False)


@mcp.tool()
def list_chats(max_chats: int = 30, scroll: bool = True) -> dict[str, Any]:
    """
    List the chats in WeChat's left sidebar, most recent first.

    Each entry has ``name``, ``preview`` (last message, "Sender: text" in
    groups), ``time`` and ``muted``. With ``scroll`` (default) the list is
    scrolled to collect up to ``max_chats`` rows; without it only the
    rows currently on screen are returned and WeChat is not activated.
    """
    try:
        with ui_session():
            logger.info("Tool list_chats called (max_chats=%d, scroll=%s)", max_chats, scroll)
            ax_app = get_wechat_ax_app(activate=scroll)
            rows = list_session_chats(ax_app, max_chats=max_chats, scroll=scroll)
            return _with_warnings(
                {
                    "chats": [row.to_dict() for row in rows],
                    "current_chat": get_current_chat_name(ax_app),
                }
            )
    except Exception as exc:
        logger.exception("Error in list_chats: %s", exc)
        return _error_result(exc)


@mcp.tool()
def check_wechat_compatibility(refresh: bool = False) -> dict[str, Any]:
    """
    Report whether the installed/running WeChat version is one this
    server was verified against, whether WeChat needs a restart after an
    update, and whether the Accessibility elements the tools depend on
    are present. Call this when a tool fails unexpectedly, or after
    WeChat updates itself.
    """
    try:
        with ui_session():
            return compatibility_report(force=refresh)
    except Exception as exc:
        logger.exception("Error in check_wechat_compatibility: %s", exc)
        return {"error": str(exc), "version": get_version_info().to_dict()}


@mcp.tool()
def add_contact_by_wechat_id(
    wechat_id: str,
    friending_msg: str | None = None,
    remark: str | None = None,
    tags: str | None = None,
    privacy: str | None = None,
    hide_my_posts: bool = False,
    hide_their_posts: bool = False,
) -> dict[str, Any]:
    """
    Add a new contact using a WeChat ID.

    This tool automates the WeChat flow:
    - Type the given WeChat ID into the global search box.
    - Click the "Search WeChat ID" card in the search results.
    - In the "Add Contacts" window, click "Add to Contacts" (or report
      ``stage: account_not_found`` when WeChat knows no such account).
    - In the "Send Friend Request" window, optionally customize the
      friending message, remark, and privacy options, then confirm.

    The `privacy` argument controls the "Privacy" section of the
    friend-request window:
    - "all" (default) selects "Chats, Moments, WeRun, etc." and applies
      the `hide_my_posts` / `hide_their_posts` flags.
    - "chats_only" selects "Chats Only" and ignores the hide flags.
    """
    logger.info(
        "Tool add_contact_by_wechat_id called for ID=%s (privacy=%r, hide_my_posts=%s, hide_their_posts=%s)",
        wechat_id,
        privacy,
        hide_my_posts,
        hide_their_posts,
    )
    try:
        with ui_session():
            result = ax_add_contact_by_wechat_id(
                wechat_id=wechat_id,
                friending_msg=friending_msg,
                remark=remark,
                tags=tags,
                privacy=privacy,
                hide_my_posts=hide_my_posts,
                hide_their_posts=hide_their_posts,
            )
            return _with_warnings(result)
    except Exception as exc:
        logger.exception("Error in add_contact_by_wechat_id for ID=%s: %s", wechat_id, exc)
        return _error_result(exc, wechat_id=wechat_id)


@mcp.tool()
def publish_moment_without_media(
    content: str,
    publish: bool = True,
) -> dict[str, Any]:
    """
    Publish a Moments post containing only text (no media).

    This will:
    - Show Moments (Window menu -> Moments, or Discover -> Moments).
    - Long-press the toolbar "Post" button to open the text composer.
    - Fill the text entry area with the provided content.
    - If `publish` is True (default), click "Post" and wait for the
      composer to close; if False, leave the composer open without
      posting so the draft can be reviewed.
    """
    logger.info(
        "Tool publish_moment_without_media called (content_length=%d, publish=%s)",
        len(content) if isinstance(content, str) else -1,
        publish,
    )
    try:
        with ui_session():
            result = ax_publish_moment(content=content, publish=publish)
            return _with_warnings(result)
    except Exception as exc:
        logger.exception("Error in publish_moment_without_media: %s", exc)
        return _error_result(exc, content=content)


def _log_startup_compatibility() -> None:
    info = get_version_info()
    logger.info(
        "WeChat version: installed=%s running=%s status=%s tested=%s",
        info.installed_version,
        info.running_version,
        info.status,
        ",".join(info.tested_versions),
    )
    for warning in info.warnings:
        logger.warning(warning)


def main() -> None:
    """
    Entry point for the WeChat MCP server.
    """
    parser = argparse.ArgumentParser(description="WeChat Helper MCP Server")
    parser.add_argument(
        "--mcp-debug",
        action="store_true",
        help="Enable detailed MCP protocol debugging logs",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print the WeChat compatibility report as JSON and exit",
    )

    args = parser.parse_args()

    if args.check:
        import json

        print(json.dumps(compatibility_report(force=True), indent=2, ensure_ascii=False))
        return

    if args.mcp_debug:
        logging.getLogger("mcp").setLevel(logging.DEBUG)
        logging.getLogger("anyio").setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

        debug_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(funcName)s:%(lineno)d - %(message)s"
        )
        for handler in logging.getLogger().handlers:
            handler.setFormatter(debug_formatter)

    logger.info("Starting WeChat Helper MCP Server")
    logger.info("Transport: %s", args.transport)
    logger.info("MCP Debug mode: %s", args.mcp_debug)
    _log_startup_compatibility()

    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http")
    elif args.transport == "sse":
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
