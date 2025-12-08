<div align="center">

# WeChat MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/wechat-mcp-server.svg)](https://pypi.org/project/wechat-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文](docs/README_zh.md) | English

</div>

An MCP server that automates WeChat on macOS using the Accessibility API and screen capture. It enables LLMs to interact with WeChat chats programmatically.

## Features

- 📨 Fetch recent messages from any chat (contact or group)
- ✍️ Send automated replies based on chat history
- 🤖 6 specialized Claude Code sub-agents for smart WeChat automation
- 🔍 Smart chat search with exact name matching
- 📜 Full message history scrolling and capture

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
2. Add your terminal application (Terminal.app, iTerm2, etc.)
3. Ensure WeChat is running before using the server

## Usage

### Basic Commands

```bash
# Run with default stdio transport
wechat-mcp --transport stdio

# Run with HTTP transport
wechat-mcp --transport streamable-http --port 3001

# Run with SSE transport
wechat-mcp --transport sse --port 3001
```

### Available MCP Tools

- **`fetch_messages_by_chat`** - Get recent messages from a chat
- **`reply_to_messages_by_chat`** - Send a reply to a chat

See [detailed API documentation](docs/detailed-guide.md) for full tool specifications.

## Claude Code Sub-Agents

This project includes 6 intelligent sub-agents designed specifically for WeChat automation. They enable natural language control of WeChat through Claude Code.

### Available Sub-Agents

1. **聊天记录总结器 (chat-summarizer)** - Summarize chat history and extract key information
2. **消息撰写发送器 (message-composer)** - Compose and send context-aware messages
3. **自动回复器 (auto-replier)** - Auto-generate and send appropriate replies
4. **消息搜索器 (message-searcher)** - Search chat history for specific content
5. **多聊天监控器 (multi-chat-checker)** - Monitor multiple chats and prioritize messages
6. **聊天洞察分析器 (chat-insights)** - Analyze relationship dynamics and communication patterns

📖 [View complete sub-agents guide](.claude/agents/README.md)

### Quick Examples

Claude would automatically select the right sub-agent for you.

```
# Summarize a chat
帮我总结一下和小明的聊天

# Send a message
帮我给老板发消息，说项目已经完成了

# Auto-reply
帮我回复一下李总

# Search messages
在和小明的聊天里找一下我们约的见面时间

# Check multiple chats
看看小明、小红和工作群有什么新消息

# Analyze relationship
分析一下我和女朋友的聊天
```

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
```

## Documentation

- 📘 [Detailed Guide](docs/detailed-guide.md) - Complete API documentation and architecture
- 🤖 [Sub-Agents Guide](.claude/agents/README.md) - How to use Claude Code sub-agents

## Requirements

- macOS (uses Accessibility API)
- WeChat for Mac installed and running
- Python 3.12+
- Accessibility permissions for terminal

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details
