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

3. To run any script or the MCP server within the environment:

   ```bash
   uv run python list_chats.py
   # or
   uv run wechat-mcp --mcp-debug
   ```

## Add the MCP server to configuration

<details>
  <summary>Claude Code</summary>
```bash
claude mcp add --transport stdio wechat-mcp --env WECHAT_MCP_AI_PROVIDER=ollama WECHAT_MCP_AI_MODEL=qwen2.5:14b -- uv --directory {path/to/wechat-mcp} run wechat-mcp --transport stdio
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
  Opens the chat for `contact_name` (first via the left session list, then via the search box if needed) and returns up to `last_n` recent messages from that chat. Each message is a JSON object:

  ```json
  {
    "sender": "ME" | "OTHER" | "UNKNOWN",
    "text": "message text"
  }
  ```

- `reply_to_messages_by_contact(contact_name: str, instructions: str | None = None, last_n: int = 50) -> dict`
  Opens the chat, fetches recent messages as above, calls a configured LLM to generate a reply, and sends the reply using the Accessibility-based `send_message` helper. Returns:

  ```json
  {
    "contact_name": "The contact",
    "generated_reply": "The message that was sent",
    "message_count": 42
  }
  ```

If an error occurs, the tools return an object containing an `"error"` field describing the issue.

## AI provider configuration

Reply generation uses an OpenAI-compatible chat completion API. Configuration is controlled via environment variables:

### Provider selection

- `WECHAT_MCP_AI_PROVIDER` – must be either:
  - `openai`
  - `ollama`

If not set, it defaults to `openai`.

### OpenAI provider

Required:

- `WECHAT_MCP_AI_API_KEY` – API key for the OpenAI-compatible provider
- `WECHAT_MCP_AI_MODEL` – model name (e.g. `gpt-4.1-mini`)

Optional:

- `WECHAT_MCP_AI_BASE_URL` – overrides the default `https://api.openai.com/v1`

### Ollama provider

Required:

- `WECHAT_MCP_AI_MODEL` – model name (e.g. `llama3.1:8b-instruct`)

Optional:

- `WECHAT_MCP_AI_BASE_URL` – overrides the default `http://localhost:11434/v1`

For Ollama, no real API key is required; a placeholder key is used if `WECHAT_MCP_AI_API_KEY` is not set.

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
