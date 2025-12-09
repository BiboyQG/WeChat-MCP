# PR: Add contact-by-WeChat-ID MCP tool

## Summary

This PR adds a new MCP tool, `add_contact_by_wechat_id`, and the underlying Accessibility helpers to let LLMs add a WeChat contact by WeChat ID, configure the friend request, and send it automatically.

## Motivation

- Enable LLMs to bootstrap new conversations, not just operate on existing chats.
- Reuse WeChat’s built-in “Add Contacts” and “Send Friend Request” flows instead of relying on brittle screen coordinates.
- Provide a structured API around friending message, remark, and privacy options so the LLM can reason about them explicitly.

## Changes

### New MCP tool

**File**: `src/wechat_mcp/mcp_server.py`

- Register a new tool:
  - `add_contact_by_wechat_id(wechat_id, friending_msg=None, remark=None, tags=None, privacy=None, hide_my_posts=False, hide_their_posts=False) -> dict`
- Delegates to the Accessibility helper in `wechat_accessibility.py`.
- Logs the requested privacy mode and hide flags and returns either:
  - A dict summarizing applied settings, or
  - A dict with `"error"` and `"stage"` when something goes wrong.

### Accessibility implementation

**File**: `src/wechat_mcp/wechat_accessibility.py`

- Add support functions for the WeChat ID add-contact flow:
  - `_click_more_card_by_title(ax_app, label)` – Find and click a search result card by visible label (e.g. `"Search WeChat ID"`).
  - `_find_window_by_title` / `_wait_for_window` – Locate and wait for WeChat windows such as `"Add Contacts"` and `"Send Friend Request"`.
  - `_click_add_to_contacts_button(add_contacts_window)` – Click the `"Add to Contacts"` button (AXButton with identifier `add_friend_button` or matching title).
  - `_set_checkbox_state` / `_set_checkbox_by_title` – Ensure `"Hide My Posts"` / `"Hide Their Posts"` checkboxes are in the desired state.
  - `_click_privacy_option(window, label)` – Select `"Chats, Moments, WeRun, etc."` or `"Chats Only"` based on the associated label row.
  - `_configure_friend_request_window(...)` – Apply friending message, remark, privacy choice, and post-visibility options in the `"Send Friend Request"` window and return the normalized privacy mode.
- Add the high-level helper:
  - `add_contact_by_wechat_id(wechat_id, friending_msg, remark, tags, privacy, hide_my_posts, hide_their_posts) -> dict`
  - Flow:
    1. Use `focus_and_type_search` to type the WeChat ID into global search.
    2. Click the `"Search WeChat ID"` result card.
    3. Wait for `"Add Contacts"` and click `"Add to Contacts"`.
    4. Wait for `"Send Friend Request"` and call `_configure_friend_request_window(...)`.
    5. Click `"OK"` to send the friend request.
  - On error, returns `{"error": ..., "wechat_id": ..., "stage": ...}` and logs the exception.

### Documentation

**File**: `docs/detailed-guide.md`

- Under “Tools exposed to MCP clients”, document:
  - `add_contact_by_wechat_id(...)` signature, behavior, and return shape.
- Under Architecture:
  - Update `mcp_server.py` section to list `add_contact_by_wechat_id(...)` as a tool.
  - Add a **Contact management** subsection in `wechat_accessibility.py` describing the new helper and its support functions.
- Mark TODO item “Add contact using WeChat ID” as completed.

**File**: `README.md`

- Add feature bullet:
  - “Add contacts using WeChat ID with configurable privacy”.
- Under “Available MCP Tools”, list:
  - `add_contact_by_wechat_id` – Add a new contact using a WeChat ID and send a friend request.

**File**: `docs/README_zh.md`

- Add feature bullet:
  - “通过微信号添加联系人并配置隐私选项”.
- Under “可用的 MCP 工具”, list:
  - `add_contact_by_wechat_id` – 通过微信号添加联系人并发送好友申请。

## How to verify

### 1. Run the MCP server

```bash
uv sync
uv run wechat-mcp --transport stdio
```

Ensure:

- WeChat (macOS) is running.
- The terminal app has Accessibility permissions.

### 2. Call the new tool from an MCP client

Example (pseudo-JSON for the tool call):

```json
{
  "tool": "add_contact_by_wechat_id",
  "args": {
    "wechat_id": "some-wechat-id",
    "friending_msg": "Hi, this is a test request from WeChat-MCP.",
    "remark": "Test Contact from MCP",
    "tags": "friends,test",
    "privacy": "all",
    "hide_my_posts": false,
    "hide_their_posts": true
  }
}
```

Observed behavior:

1. The global search field in WeChat is focused and filled with `wechat_id`.
2. The `"Search WeChat ID"` card in the search results is clicked.
3. The `"Add Contacts"` window appears and `"Add to Contacts"` is pressed.
4. The `"Send Friend Request"` window appears:
   - Friending message updates (if provided).
   - Remark updates (if provided).
   - Privacy and checkboxes are set according to `privacy`, `hide_my_posts`, and `hide_their_posts`.
5. `"OK"` is clicked and the friend request is sent.

### 3. Error handling

- Try an obviously invalid WeChat ID and verify that the tool:
  - Returns an `"error"` field with a human-readable description.
  - Includes `"stage"` indicating where the flow failed (e.g. `"search_wechat_id"`, `"add_contacts_window"`, `"send_friend_request_window"`, `"confirm_request"`).

## Environment details (fill before opening PR)

- macOS version: `TODO (e.g. macOS 15.x Sequoia)`
- WeChat for Mac version: `TODO (e.g. 3.x.x)`
- Python version: `TODO (e.g. 3.12.x via uv)`

## Potential risks / considerations

- WeChat UI changes (window titles, control titles, or identifiers such as `add_friend_button`) could break the flow; logging should make these failures easy to diagnose.
- The implementation assumes a standard macOS scroll and Accessibility configuration; third-party tools that alter window behavior or input handling might interfere.
- The `tags` parameter is currently a placeholder and is logged but not yet wired through to the UI.

