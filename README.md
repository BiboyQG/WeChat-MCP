# WeChat MCP Server

This project provides an MCP server that automates WeChat on macOS using the Accessibility API and screen capture. It exposes tools that LLMs can call to:

- Fetch recent messages for a specific chat (contact or group)
- Generate and send a reply to a chat based on recent history

## Installation

The WeChat MCP server is published on PyPI as `wechat-mcp-server` and installs a `wechat-mcp` console script.

```bash
pip install wechat-mcp-server
```

You can still use [`uv`](https://github.com/astral-sh/uv) for local development and dependency management when working with this repository.

## Environment setup (using `uv`)

For local development, this project uses `uv` to manage the environment.

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
# For pip
claude mcp add --transport stdio wechat-mcp -- wechat-mcp
# For uv
claude mcp add --transport stdio wechat-mcp -- uv --directory $(pwd) run wechat-mcp
```

</details>

<details>
  <summary>Codex</summary>

```bash
# For pip
codex mcp add wechat-mcp -- wechat-mcp
# For uv
codex mcp add wechat-mcp -- uv --directory $(pwd) run wechat-mcp
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

- `fetch_messages_by_chat(chat_name: str, last_n: int = 50) -> list[dict]`
  Opens the chat for `chat_name` (first via the left session list, then via the global search box if needed). When using global search it prefers an **exact name match** in the "Contacts" section, then in the "Group Chats" section, and explicitly ignores matches under "Chat History", "Official Accounts", or "More". If no exact match is found, it does **not** fall back to the top search result; instead it returns a structured error plus up to 15 candidate names from each of "Contacts" and "Group Chats" so the LLM can choose a more specific target. Once a chat is successfully opened, it uses scrolling plus screenshots to collect the **true last** `last_n` messages, even if they span multiple screens of history. Each message is a JSON object:

  ```json
  {
    "sender": "ME" | "OTHER" | "UNKNOWN",
    "text": "message text"
  }
  ```

- `reply_to_messages_by_chat(chat_name: str, reply_message: str | null = null) -> dict`
  Ensures the chat for `chat_name` is open (skipping an extra click when the current chat already matches), and (optionally) sends the provided `reply_message` using the Accessibility-based `send_message` helper. This tool is intended to be driven by the LLM that is already using this MCP: first call `fetch_messages_by_chat`, then compose a reply, then call this tool with that reply. Returns:

  ```json
  {
    "chat_name": "The chat (contact or group)",
    "reply_message": "The message that was sent (or null)",
    "sent": true
  }
  ```

If an error occurs, the tools return an object containing an `"error"` field describing the issue.

Internally, `fetch_messages_by_chat` scrolls the WeChat message list using the system’s standard macOS scroll semantics (no third‑party scroll reversal tools enabled) and continues scrolling until it has assembled the true last `last_n` messages or reached the beginning of the chat history, rather than stopping after a fixed number of scroll steps.

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
- [x] Prefer exact match in Contacts/Group Chats search results
- [ ] Support WeChat with Chinese language
