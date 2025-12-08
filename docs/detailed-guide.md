# WeChat MCP Server - Detailed Guide

This document provides detailed information about the WeChat MCP server implementation, architecture, and usage.

## Overview

This project provides an MCP server that automates WeChat on macOS using the Accessibility API and screen capture. It exposes tools that LLMs can call to:

- Fetch recent messages for a specific chat (contact or group)
- Generate and send a reply to a chat based on recent history

## Tools exposed to MCP clients

The server is implemented in `src/wechat_mcp/mcp_server.py` and defines two `@mcp.tool()` functions:

### `fetch_messages_by_chat`

**Signature**: `fetch_messages_by_chat(chat_name: str, last_n: int = 50) -> list[dict]`

Opens the chat for `chat_name` (first via the left session list, then via the global search box if needed). When using global search it prefers an **exact name match** in the "Contacts" section, then in the "Group Chats" section, and explicitly ignores matches under "Chat History", "Official Accounts", or "More". If no exact match is found, it does **not** fall back to the top search result; instead it returns a structured error plus up to 15 candidate names from each of "Contacts" and "Group Chats" so the LLM can choose a more specific target. Once a chat is successfully opened, it uses scrolling plus screenshots to collect the **true last** `last_n` messages, even if they span multiple screens of history. Each message is a JSON object:

```json
{
  "sender": "ME" | "OTHER" | "UNKNOWN",
  "text": "message text"
}
```

### `reply_to_messages_by_chat`

**Signature**: `reply_to_messages_by_chat(chat_name: str, reply_message: str | null = null) -> dict`

Ensures the chat for `chat_name` is open (skipping an extra click when the current chat already matches), and (optionally) sends the provided `reply_message` using the Accessibility-based `send_message` helper. This tool is intended to be driven by the LLM that is already using this MCP: first call `fetch_messages_by_chat`, then compose a reply, then call this tool with that reply. Returns:

```json
{
  "chat_name": "The chat (contact or group)",
  "reply_message": "The message that was sent (or null)",
  "sent": true
}
```

If an error occurs, the tools return an object containing an `"error"` field describing the issue.

Internally, `fetch_messages_by_chat` scrolls the WeChat message list using the system's standard macOS scroll semantics (no third‑party scroll reversal tools enabled) and continues scrolling until it has assembled the true last `last_n` messages or reached the beginning of the chat history, rather than stopping after a fixed number of scroll steps.

## Architecture

### Core Components

The project consists of several key modules:

#### `src/wechat_mcp/mcp_server.py`

The main MCP server implementation that:
- Creates a `FastMCP` server instance
- Defines the two tool functions decorated with `@mcp.tool()`
- Handles multiple transport types (stdio, streamable-http, sse)
- Provides the main entry point via the `main()` function

#### `src/wechat_mcp/wechat_accessibility.py`

Contains all the low-level Accessibility API interactions:

**Low-level Accessibility API helpers:**
- `ax_get(element, attribute)` - Get accessibility element attributes
- `dfs(element, predicate)` - Depth-first search in accessibility tree
- `click_element_center(element)` - Synthesize mouse click
- `send_key_with_modifiers(keycode, flags)` - Keyboard input simulation

**WeChat app interaction:**
- `get_wechat_ax_app()` - Get/activate WeChat application
- `get_current_chat_name()` - Get title of currently open chat
- `_normalize_chat_title(name)` - Strip group member count suffix like "(23)"

**Chat navigation:**
- `find_chat_element_by_name(ax_app, chat_name)` - Find chat in session list
- `open_chat_for_contact(chat_name)` - Open chat with smart fallback behavior:
  1. First tries sidebar session list
  2. If not found, uses global search with preference for exact matches
  3. Prioritizes "Contacts" over "Group Chats"
  4. Ignores "Chat History", "Official Accounts", "Internet search results"
  5. Returns error + candidates list if no exact match found

**Search functionality:**
- `find_search_field(ax_app)` - Locate WeChat search input
- `focus_and_type_search(ax_app, text)` - Type into search via clipboard + keyboard
- `get_search_list(ax_app)` - Find search results list
- `_expand_section_if_needed(search_list, section_title)` - Click "View All"
- `_select_contact_from_search_results(ax_app, contact_name)` - Smart search with scrolling
- `_summarize_search_candidates(entries)` - Extract up to 15 contact + group names

**Message fetching:**
- `get_messages_list(ax_app)` - Find "Messages" list in UI
- `fetch_recent_messages(last_n=100, max_scrolls=None)` - Core algorithm:
  1. Scrolls to bottom (newest messages)
  2. Repeatedly scrolls up in small steps
  3. Captures screenshot of message area at each position
  4. Collects visible messages and their positions/sizes
  5. Classifies sender as "ME"/"OTHER"/"UNKNOWN" using pixel analysis
  6. Merges newly revealed older messages by aligning on anchor text
  7. Continues until `last_n` messages collected or history exhausted
- `capture_message_area(msg_list)` - Take screenshot of message area
- `scroll_to_bottom(msg_list, center)` - Scroll to newest messages
- `scroll_up_small(center)` - Scroll up gradually
- `post_scroll(center, delta_lines)` - Send scroll-wheel events

**Sender classification:**
- `classify_sender_for_message(image, list_origin, message_pos, message_size)` - Pixel-based heuristic
- `count_colored_pixels(image, left, top, right, bottom)` - Image processing

**Message sending:**
- `send_message(text)` - Send a message via Accessibility API
- `find_input_field(ax_app)` - Locate chat input field
- `press_return()` - Synthesize Return key press

#### `src/wechat_mcp/logging_config.py`

Configures dual logging:
- File handler: writes to `logs/wechat_mcp.log` (DEBUG level)
- Console handler: writes to stdout (INFO level)
- Customizable via `WECHAT_MCP_LOG_DIR` environment variable

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

## Dependencies

From `pyproject.toml`:

```
pyobjc >= 12.1                          # macOS accessibility bridge
pyobjc-framework-applicationservices   # Accessibility frameworks
pillow >= 10.0.0                        # Image processing for sender detection
mcp[cli] >= 1.0.0                       # MCP server framework
```

## Supported Transports

The MCP server supports multiple transport protocols:

- **stdio** (default) - Standard input/output for local process communication
- **streamable-http** - HTTP-based streaming transport (requires `--port`)
- **sse** - Server-Sent Events transport (requires `--port`)

Example usage:

```bash
# stdio (default)
wechat-mcp --transport stdio

# HTTP streaming
wechat-mcp --transport streamable-http --port 3001

# Server-Sent Events
wechat-mcp --transport sse --port 3001
```

## Development

For local development using `uv`:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync environment
cd WeChat-MCP
uv sync

# Run the server
uv run wechat-mcp --transport stdio
```

## Troubleshooting

### Accessibility Permissions

If you get errors about accessibility permissions:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Add your terminal application (Terminal.app, iTerm2, etc.)
3. Enable the checkbox for that application
4. Restart your terminal

### WeChat Not Found

Make sure WeChat is running before starting the MCP server. The bundle identifier is `com.tencent.xinWeChat`.

### Search Not Finding Contacts

The search implementation prefers exact matches. If a contact name is not found:

1. The server will return a list of similar candidates
2. The LLM can choose the correct one from the list
3. Make sure the contact name matches exactly (case-insensitive)

## TODO

- [x] Detect and switch to contact by clicking
- [x] Scroll to get full/more history messages
- [x] Prefer exact match in Contacts/Group Chats search results
- [ ] Support WeChat with Chinese language
- [ ] Identify OTHER with explicit name
