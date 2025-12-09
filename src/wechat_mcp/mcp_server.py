from __future__ import annotations

import argparse
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .logging_config import logger
from .wechat_accessibility import (
    ChatMessage,
    add_contact_by_wechat_id as ax_add_contact_by_wechat_id,
    fetch_recent_messages,
    get_current_chat_name,
    open_chat_for_contact,
    send_message,
)


mcp = FastMCP("WeChat Helper MCP Server")


@mcp.tool()
def fetch_messages_by_chat(
    chat_name: str,
    last_n: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch recent messages for a specific chat (contact or group).

    This will:
    - Look for the chat in the left sidebar session list
    - If found, click it to open the chat
    - If not found, search for the chat via the search box
    - Once the chat is open, retrieve recent messages from that chat
    """
    try:
        logger.info("Tool fetch_messages_by_chat called for chat=%s", chat_name)
        current_chat = get_current_chat_name()
        same_chat = current_chat == chat_name if current_chat is not None else False
        logger.info(
            "Current chat title=%r, target=%r, same_chat=%s",
            current_chat,
            chat_name,
            same_chat,
        )
        if not same_chat:
            open_result = open_chat_for_contact(chat_name)
            if isinstance(open_result, dict) and open_result.get("error"):
                # No exact match; surface candidates instead of forcing a chat.
                logger.info(
                    "open_chat_for_contact returned candidates for chat=%s; "
                    "skipping message fetch",
                    chat_name,
                )
                enriched = dict(open_result)
                enriched.setdefault("tool", "fetch_messages_by_chat")
                return [enriched]

        messages: list[ChatMessage] = fetch_recent_messages(last_n=last_n)
        result = [msg.to_dict() for msg in messages]
        logger.info("Returning %d messages for chat=%s", len(result), chat_name)
        return result
    except Exception as exc:
        logger.exception(
            "Error in fetch_messages_by_chat for chat=%s: %s",
            chat_name,
            exc,
        )
        return [
            {
                "error": str(exc),
                "chat_name": chat_name,
            }
        ]


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

    If reply_message is None or empty, no message is sent; the tool still
    ensures the chat is open.
    """
    logger.info(
        "Tool reply_to_messages_by_chat called for chat=%s (has_reply=%s)",
        chat_name,
        bool(reply_message),
    )
    try:
        current_chat = get_current_chat_name()
        same_chat = current_chat == chat_name if current_chat is not None else False
        logger.info(
            "Current chat title=%r, target=%r, same_chat=%s",
            current_chat,
            chat_name,
            same_chat,
        )
        if not same_chat:
            open_result = open_chat_for_contact(chat_name)
            if isinstance(open_result, dict) and open_result.get("error"):
                logger.info(
                    "open_chat_for_contact returned candidates for chat=%s; "
                    "skipping reply send",
                    chat_name,
                )
                enriched: dict[str, Any] = {
                    "error": open_result.get("error"),
                    "chat_name": chat_name,
                    "candidates": open_result.get("candidates", {}),
                    "reply_message": reply_message,
                    "sent": False,
                    "tool": "reply_to_messages_by_chat",
                }
                return enriched

        sent = False
        if reply_message is not None and reply_message.strip():
            send_message(reply_message)
            sent = True
            logger.info(
                "Reply sent to chat=%s; message length=%d",
                chat_name,
                len(reply_message),
            )

        return {
            "chat_name": chat_name,
            "reply_message": reply_message,
            "sent": sent,
        }
    except Exception as exc:
        logger.exception(
            "Error in reply_to_messages_by_chat for chat=%s: %s",
            chat_name,
            exc,
        )
        return {
            "error": str(exc),
            "chat_name": chat_name,
        }


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
    - Click the "Search WeChat ID" card under the "More" section.
    - In the "Add Contacts" window, click "Add to Contacts".
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
        result = ax_add_contact_by_wechat_id(
            wechat_id=wechat_id,
            friending_msg=friending_msg,
            remark=remark,
            tags=tags,
            privacy=privacy,
            hide_my_posts=hide_my_posts,
            hide_their_posts=hide_their_posts,
        )
        return result
    except Exception as exc:
        logger.exception(
            "Error in add_contact_by_wechat_id for ID=%s: %s",
            wechat_id,
            exc,
        )
        return {
            "error": str(exc),
            "wechat_id": wechat_id,
        }


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
        "--port",
        type=int,
        default=3001,
        help="Port for HTTP transport (default: 3001)",
    )

    args = parser.parse_args()

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

    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", port=args.port)


if __name__ == "__main__":
    main()
