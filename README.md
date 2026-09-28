<div align="center">

# WeChat MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/wechat-mcp-server.svg)](https://pypi.org/project/wechat-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](docs/README_zh.md) | English

</div>

An MCP server that automates WeChat on macOS using the Accessibility API and window capture. It enables LLMs to interact with WeChat chats programmatically.

> Built for **WeChat for Mac 4.x** (verified on 4.1.13, English UI). The server checks the installed/running WeChat version on every call and tells you when WeChat was updated to a version that has not been verified yet (see [Compatibility checks](#compatibility-checks)).

## Features

- 📨 Fetch recent messages from any chat (contact or group), with sender (`ME`/`OTHER`/`SYSTEM`), message kind and, in group chats, the member name
- 🗂 List the sidebar chats with last-message preview, time and mute state
- ✍️ Send replies only after verifying the right chat is open; each send is confirmed against the newest bubble
- 🧭 Reads chats without stealing focus where possible and gives the foreground back to the app you were using
- 🩺 Detects WeChat updates (untested version, pending restart, missing UI elements)
- 📷 Publish text-only Moments posts, with optional draft-only mode
- 👥 Add contacts using WeChat ID with configurable privacy
- 🔍 Smart chat search with exact name matching
- 🤖 5 specialized Claude Code sub-agents for smart WeChat automation

## Quick Start

### Installation

```bash
pip install wechat-mcp-server
```

### Setup with Claude Code

```bash
# If installed via pip
claude mcp add --transport stdio wechat-mcp -- wechat-mcp

# If using uv for development
claude mcp add --transport stdio wechat-mcp -- uv --directory $(pwd) run wechat-mcp
```

<details>
<summary>Setup with Claude Desktop</summary>

```json
// If installed via pip
{
  "mcpServers": {
    "wechat-mcp": {
      "type": "stdio",
      "command": "wechat-mcp"
    }
  }
}

// If using uv for development
{
  "mcpServers": {
    "wechat-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "{path/to/wechat-mcp}",
        "run",
        "wechat-mcp"
      ],
    }
  }
}
```

</details>

<details>
<summary>Setup with Codex</summary>

```bash
# If installed via pip
codex mcp add wechat-mcp -- wechat-mcp

# If using uv for development
codex mcp add wechat-mcp -- uv --directory $(pwd) run wechat-mcp
```

</details>

### macOS Permissions

⚠️ **Important**: Grant Accessibility permissions to your terminal:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Add your terminal application (Terminal.app, iTerm2, etc.) or the MCP host
3. Also grant **Screen Recording** to the same app: it is used to tell your own bubbles from incoming ones and to read member names in group chats. Without it the server falls back to a screen grab and needs WeChat in front.
4. Ensure WeChat is running (and on the Chats tab) before using the server

## Usage

### Basic Commands

```bash
# Run with default stdio transport
wechat-mcp --transport stdio

# Run with HTTP transport
wechat-mcp --transport streamable-http

# Run with SSE transport
wechat-mcp --transport sse

# Print the WeChat version / UI compatibility report and exit
wechat-mcp --check
```

### Available MCP Tools

- **`fetch_messages_by_chat`** - Get recent messages from a chat (`sender`, `sender_name`, `kind`, `text`)
- **`reply_to_messages_by_chat`** - Send a reply to a chat (refuses to send if a different chat is open; reports `verified`)
- **`list_chats`** - List sidebar chats with preview, time and mute state
- **`check_wechat_compatibility`** - Version and UI compatibility report
- **`add_contact_by_wechat_id`** - Add a new contact using a WeChat ID and send a friend request
- **`publish_moment_without_media`** - Publish a text-only Moments post (no photos or videos); optionally only prepare a draft without posting via `publish=False`

### Command line (`wechat-cli`)

The same operations are available from the shell, which is what the sibling `wechat-automation` Claude skill uses. Every command prints JSON (or `--text`) and exits non-zero on failure.

```bash
wechat-cli --text chats --max 20            # sidebar chats
wechat-cli --text fetch "Team" -n 50        # recent messages
wechat-cli --text send "Team" "on my way"   # send (verified)
wechat-cli --text open "Team"               # open without sending
wechat-cli --text check                     # version / UI compatibility
wechat-cli moment "text only" --draft       # Moments composer, no post
wechat-cli add-contact wxid_xxx --message "hi"
```

### Compatibility checks

Tencent changes WeChat's Accessibility layout between releases. The server therefore:

- records the versions it was verified against (`TESTED_WECHAT_VERSIONS` in `src/wechat_mcp/compat.py`, currently `4.1.13`);
- reads the installed and the running WeChat version on every tool call and adds a `warnings` entry when the version is newer/older than verified or when WeChat was updated but not restarted;
- probes the main window for the UI elements the tools rely on (`session_list`, search field, `chat_message_list`, `chat_input_field`, `current_chat_name_label`) and, when a tool fails, attaches a `diagnostics` block naming the missing elements;
- exposes all of this via the `check_wechat_compatibility` tool and `wechat-mcp --check`.

After verifying a new WeChat release yourself, add it to `TESTED_WECHAT_VERSIONS` or set `WECHAT_MCP_ACKNOWLEDGED_VERSIONS=4.2.0` to silence the warning.

### Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `WECHAT_MCP_LOG_DIR` | `logs` | Directory for `wechat_mcp.log` |
| `WECHAT_MCP_RESTORE_FOCUS` | `1` | Give the foreground back to the previous app after each tool |
| `WECHAT_MCP_ACKNOWLEDGED_VERSIONS` | – | Comma-separated WeChat versions to treat as verified |

See [detailed API documentation](docs/detailed-guide.md) for full tool specifications.

## Claude Code Sub-Agents

This project includes 5 intelligent sub-agents designed specifically for WeChat automation. They enable natural language control of WeChat through Claude Code.

### Available Sub-Agents

1. **Chat-summarizer** - Summarize chat history and extract key information
2. **Auto-replier** - Auto-generate and send appropriate replies
3. **Message-searcher** - Search chat history for specific content
4. **Multi-chat-checker** - Monitor multiple chats and prioritize messages
5. **Chat-insights** - Analyze relationship dynamics and communication patterns

📖 [View complete sub-agents guide](.claude/agents/README.md)

## Development

### Local Setup with uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/yourusername/WeChat-MCP.git
cd WeChat-MCP
uv sync

# Run locally
uv run wechat-mcp --transport stdio

# Unit tests (no WeChat needed: they run against a fake Accessibility tree)
uv run pytest
```

## Documentation

- 📘 [Detailed Guide](docs/detailed-guide.md) - Complete API documentation and architecture
- 🤖 [Sub-Agents Guide](.claude/agents/README.md) - How to use Claude Code sub-agents

## Requirements

- macOS (uses Accessibility API and window capture)
- WeChat for Mac 4.x installed and running (verified on 4.1.13; 3.x has a different UI)
- Python 3.12+
- Accessibility and Screen Recording permissions for the terminal / MCP host

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details
