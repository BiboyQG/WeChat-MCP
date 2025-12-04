# WeChat MCP Server

This project provides an MCP server that automates WeChat on macOS using the Accessibility API and screen capture. It exposes tools that LLMs can call to:

- Fetch recent messages for a specific contact
- Generate and send a reply to a contact based on recent history

## Environment setup (using `uv`)

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency and environment management.

1. Install `uv` (if not already installed):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. From the project root, create/sync the environment:

   ```bash
   cd WeChat-MCP
   uv sync
   ```

   This will create a virtual environment (if needed) and install dependencies defined in `pyproject.toml`.

## Add the MCP server to configuration

<details>
  <summary>Claude Code</summary>

```bash
claude mcp add --transport stdio wechat-mcp -- uv --directory $(pwd) run wechat-mcp
```

</details>

The MCP server entrypoint is `wechat_mcp.mcp_server:main`, exposed as the `wechat-mcp` console script.

Typical invocation:

```bash
uv run wechat-mcp --transport stdio
```

Supported transports:

- `stdio` (default)
- `streamable-http` (with `--port`, default `3001`)
- `sse` (with `--port`, default `3001`)

Example:

```bash
uv run wechat-mcp --transport streamable-http --port 3001
```

## Tools exposed to MCP clients

The server is implemented in `src/wechat_mcp/mcp_server.py` and defines two `@mcp.tool()` functions:

- `fetch_messages_by_contact(contact_name: str, last_n: int = 50) -> list[dict]`
  Opens the chat for `contact_name` (first via the left session list, then via the search box if needed), then uses scrolling plus screenshots to collect the **true last** `last_n` messages, even if they span multiple screens of history. Each message is a JSON object:

  ```json
  {
    "sender": "ME" | "OTHER" | "UNKNOWN",
    "text": "message text"
  }
  ```

- `reply_to_messages_by_contact(contact_name: str, reply_message: str | null = null, last_n: int = 50) -> dict`
  Ensures the chat for `contact_name` is open (skipping an extra click when the current chat already matches), and (optionally) sends the provided `reply_message` using the Accessibility-based `send_message` helper. This tool is intended to be driven by the LLM that is already using this MCP: first call `fetch_messages_by_contact`, then compose a reply, then call this tool with that reply. Returns:

  ```json
  {
    "contact_name": "The contact",
    "reply_message": "The message that was sent (or null)",
    "sent": true
  }
  ```

If an error occurs, the tools return an object containing an `"error"` field describing the issue.

## Logging

The project has a comprehensive logging setup:

- Logs are written to a rotating file under the `logs/` directory (by default `logs/wechat_mcp.log`)
- Logs are also sent to the terminal (stdout)

You can customize the log directory via:

- `WECHAT_MCP_LOG_DIR` – directory path where `.log` files should be stored (defaults to `logs` under the current working directory)

## macOS and Accessibility requirements

Because this project interacts with WeChat via the macOS Accessibility API:

- WeChat must be running (`com.tencent.xinWeChat`)
- The Python process (or the terminal app running it) must have Accessibility permissions enabled in **System Settings → Privacy & Security → Accessibility**

The helper scripts and MCP tools rely on:

- Accessibility tree inspection to find chat lists, search fields, and message lists
- Screen capture to classify message senders (`ME` vs `OTHER` vs `UNKNOWN`)
- Synthetic keyboard events to search, focus inputs, and send messages

## TODO

- [x] Detect and switch to contact by clicking
- [x] Scroll to get full/more history messages
