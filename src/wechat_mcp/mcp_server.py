from __future__ import annotations

import argparse
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .logging_config import logger
from .wechat_accessibility import ChatMessage, fetch_recent_messages, get_current_chat_name, open_chat_for_contact, send_message


mcp = FastMCP("WeChat Helper MCP Server")


@mcp.tool()
def fetch_messages_by_contact(
    contact_name: str,
    last_n: int = 50,
) -> list[dict[str, str]]:
    """
    Fetch recent messages for a specific contact.

    This will:
    - Look for the contact in the left sidebar session list
    - If found, click the contact to open the chat
    - If not found, search for the contact via the search box
    - Once the chat is open, retrieve recent messages from that chat
    """
    try:
        logger.info(
            "Tool fetch_messages_by_contact called for contact=%s", contact_name
        )
        open_chat_for_contact(contact_name)
        messages: list[ChatMessage] = fetch_recent_messages(last_n=last_n)
        result = [msg.to_dict() for msg in messages]
        logger.info("Returning %d messages for contact=%s", len(result), contact_name)
        return result
    except Exception as exc:
        logger.exception(
            "Error in fetch_messages_by_contact for contact=%s: %s",
            contact_name,
            exc,
        )
        return [
            {
                "error": str(exc),
                "contact_name": contact_name,
            }
        ]


@mcp.tool()
def reply_to_messages_by_contact(
    contact_name: str,
    reply_message: str | None = None,
) -> dict[str, Any]:
    """
    Optionally send a reply to a contact.

    This tool is designed to be driven by the LLM using this MCP:
    - Call fetch_messages_by_contact first to inspect conversation history.
    - Have the LLM compose a reply string.
    - Call this tool with that reply string to send it.

    If reply_message is None or empty, no message is sent; the tool still
    ensures the chat is open.
    """
    logger.info(
        "Tool reply_to_messages_by_contact called for contact=%s (has_reply=%s)",
        contact_name,
        bool(reply_message),
    )
    try:
        current_chat = get_current_chat_name()
        same_chat = current_chat == contact_name if current_chat is not None else False
        logger.info(
            "Current chat title=%r, target=%r, same_chat=%s",
            current_chat,
            contact_name,
            same_chat,
        )
        if not same_chat:
            open_chat_for_contact(contact_name)

        sent = False
        if reply_message is not None and reply_message.strip():
            send_message(reply_message)
            sent = True
            logger.info(
                "Reply sent to contact=%s; message length=%d",
                contact_name,
                len(reply_message),
            )

        return {
            "contact_name": contact_name,
            "reply_message": reply_message,
            "sent": sent,
        }
    except Exception as exc:
        logger.exception(
            "Error in reply_to_messages_by_contact for contact=%s: %s",
            contact_name,
            exc,
        )
        return {
            "error": str(exc),
            "contact_name": contact_name,
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
