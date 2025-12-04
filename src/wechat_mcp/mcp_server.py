from __future__ import annotations

import argparse
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .logging_config import logger
from .llm_client import generate_reply_for_contact
from .wechat_accessibility import (
    ChatMessage,
    fetch_recent_messages,
    open_chat_for_contact,
    send_message,
)


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
    instructions: str | None = None,
    last_n: int = 50,
) -> dict[str, Any]:
    """
    Generate and send a reply to a contact based on recent history.

    This will:
    - Open the chat with the specified contact (session list first, then search)
    - Retrieve recent messages using the same logic as fetch_messages_by_contact
    - Call a configured LLM to generate an appropriate reply
    - Send that reply using the WeChat Accessibility-based send_message helper
    """
    logger.info("Tool reply_to_messages_by_contact called for contact=%s", contact_name)
    try:
        open_chat_for_contact(contact_name)
        messages: list[ChatMessage] = fetch_recent_messages(last_n=last_n)
        message_dicts = [msg.to_dict() for msg in messages]

        reply_text = generate_reply_for_contact(
            contact_name=contact_name,
            messages=message_dicts,
            instructions=instructions,
        )

        send_message(reply_text)

        logger.info(
            "Reply sent to contact=%s; message length=%d",
            contact_name,
            len(reply_text),
        )

        return {
            "contact_name": contact_name,
            "generated_reply": reply_text,
            "message_count": len(message_dicts),
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
