from __future__ import annotations

from wechat_mcp.mcp_server import (
    add_contact_by_wechat_id,
    fetch_messages_by_chat,
    reply_to_messages_by_chat,
)


def main() -> None:
    """
    Simple smoke test that calls the three MCP tools directly.

    These calls are primarily intended to validate wiring after refactors.
    On systems without WeChat or Accessibility permissions, they will
    return structured error objects rather than raising.
    """
    print("=== fetch_messages_by_chat ===")
    print(fetch_messages_by_chat("家", last_n=30))

    print("=== reply_to_messages_by_chat ===")
    print(reply_to_messages_by_chat("邦邦", "Hello from tools_smoke_script"))

    print("=== add_contact_by_wechat_id ===")
    print(add_contact_by_wechat_id("wew123"))


if __name__ == "__main__":
    main()

