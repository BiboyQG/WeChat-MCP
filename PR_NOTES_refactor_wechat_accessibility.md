## PR: Refactor WeChat accessibility codebase into shared + tool-specific helpers

### Summary

This PR refactors the original monolithic `src/wechat_mcp/wechat_accessibility.py` (≈1300 lines) into a shared core module plus three tool-specific helper modules, improving readability, separation of concerns, and future maintainability while preserving existing behavior.

### Motivation

- The previous single-file design made it hard to reason about which helpers were used by which MCP tools.
- The project already conceptually groups behavior by tool:
  - `fetch_messages_by_chat`
  - `reply_to_messages_by_chat`
  - `add_contact_by_wechat_id`
- Splitting shared vs tool-specific logic clarifies responsibilities, makes future changes safer, and aligns with the TODO item in `docs/detailed-guide.md` (“Refactor wechat accessibility codebase”).

### Changes

#### 1. Shared Accessibility helpers

- **File**: `src/wechat_mcp/wechat_accessibility.py`
- Now focuses on common utilities that are reused by all tools:
  - Low-level AX helpers: `ax_get`, `dfs`, `axvalue_to_point`, `axvalue_to_size`.
  - Input/mouse helpers: `send_key_with_modifiers`, `click_element_center`.
  - WeChat app interaction: `get_wechat_ax_app`, `get_current_chat_name`, `_normalize_chat_title`.
  - Session list navigation: `collect_chat_elements`, `find_chat_element_by_name`.
  - Global search helpers:
    - `find_search_field`, `focus_and_type_search`, `get_search_list`.
    - `SearchEntry`, `_collect_search_entries`, `_build_section_headers`, `_classify_section`.
    - `_find_exact_match_in_entries`, `_summarize_search_candidates`, `_expand_section_if_needed`, `_select_contact_from_search_results`.
  - Generic list geometry/scroll helpers: `get_list_center`, `post_scroll`.
  - Chat-opening orchestration: `open_chat_for_contact`.

#### 2. Fetch-messages helpers

- **File**: `src/wechat_mcp/fetch_messages_by_chat_utils.py`
- New module that contains logic only needed by `fetch_messages_by_chat`:
  - `get_messages_list(ax_app)` – locate the “Messages” AX list.
  - `capture_message_area(msg_list)` – screenshot the visible message area.
  - `scroll_to_bottom(msg_list, center)` / `scroll_up_small(center)` – scroll strategy.
  - `count_colored_pixels(...)` – pixel sampling for bubble color.
  - `SenderLabel` and `ChatMessage` dataclass (with `.to_dict()`).
  - `classify_sender_for_message(...)` – classify `"ME"`, `"OTHER"`, `"UNKNOWN"`.
  - `fetch_recent_messages(last_n=100, max_scrolls=None)` – unchanged algorithm, moved into this module and re-wired to use shared helpers from `wechat_accessibility`.

#### 3. Reply helpers

- **File**: `src/wechat_mcp/reply_to_messages_by_chat_utils.py`
- New module that contains helpers used by `reply_to_messages_by_chat`:
  - `press_return()` – synthesize Return key press via Quartz events.
  - `find_input_field(ax_app)` – locate the chat input text area.
  - `send_message(text)` – focus input, set value, press Return, log.

#### 4. Add-contact helpers

- **File**: `src/wechat_mcp/add_contact_by_wechat_id_utils.py`
- New module dedicated to `add_contact_by_wechat_id`:
  - `_click_more_card_by_title(ax_app, label)` – click the “Search WeChat ID” card using the shared search-entry machinery.
  - `_find_window_by_title` / `_wait_for_window` – locate “Add Contacts” / “Send Friend Request” windows.
  - `_click_add_to_contacts_button(add_contacts_window)` – press “Add to Contacts”.
  - `_set_checkbox_state` / `_set_checkbox_by_title` – toggle privacy-related checkboxes.
  - `_click_privacy_option(window, label)` – choose between “Chats, Moments, WeRun, etc.” and “Chats Only”.
  - `_configure_friend_request_window(...)` – apply friending message, remark, tags placeholder, and privacy/hide flags.
  - `add_contact_by_wechat_id(...)` – orchestrates the full flow and preserves the existing structured error reporting (`stage` field, etc.).

#### 5. MCP server wiring

- **File**: `src/wechat_mcp/mcp_server.py`
- Updated imports to reflect the new module boundaries:
  - `ChatMessage`, `fetch_recent_messages` from `fetch_messages_by_chat_utils`.
  - `send_message` from `reply_to_messages_by_chat_utils`.
  - `add_contact_by_wechat_id` from `add_contact_by_wechat_id_utils`.
  - `get_current_chat_name`, `open_chat_for_contact` remain imported from the slimmer `wechat_accessibility`.
- Tool signatures and behavior are unchanged; only internal wiring moved.

#### 6. Documentation updates

- **File**: `docs/detailed-guide.md`
  - Updated the Architecture section to:
    - Describe `wechat_accessibility.py` as the shared core.
    - Introduce the three new tool-specific helpers modules and list their key functions.
  - Marked the TODO item “Refactor wechat accessibility codebase” as completed (`[x]`).

#### 7. Smoke test script

- **File**: `tests/tools_smoke_script.py`
  - Simple script to exercise the three MCP tools directly:
    - `fetch_messages_by_chat("Dummy Chat", last_n=5)`
    - `reply_to_messages_by_chat("Dummy Chat", "Hello from tools_smoke_script")`
    - `add_contact_by_wechat_id("dummy_wechat_id")`
  - Intended as a quick wiring check after refactors; it surfaces structured error dicts if WeChat/search do not find the requested chat or the friend-request flow cannot complete.

### Behavior and compatibility

- Public MCP tool signatures and JSON payload shapes are unchanged.
- Logging and error-handling behavior is preserved (including `"error"` and `"stage"` fields).
- All macOS Accessibility interactions still go through the same underlying AX/Quartz calls, now grouped by responsibility.

### Testing

- Local smoke test using uv’s virtual environment:

  ```bash
  uv run wechat-mcp --transport stdio  # (existing entry point, sanity check)

  # New smoke script that calls the three tools directly
  uv run python tests/tools_smoke_script.py
  ```

- Observed:
  - `fetch_messages_by_chat` and `reply_to_messages_by_chat` return structured error objects when the dummy chat name is not found, as before (with candidates list and `tool` field set appropriately).
  - `add_contact_by_wechat_id` runs through the “Search WeChat ID” flow and returns a structured error if the “Add to Contacts” button cannot be located.

### Notes for reviewers

- The majority of changes are mechanical moves of existing logic into new modules; where logic was moved, it was copied verbatim and then removed from `wechat_accessibility.py`.
- Shared helpers remain in `wechat_accessibility.py` to minimise duplication and keep all low-level AX utilities in one place, per the project guidelines.
- If you prefer different file names (e.g. shorter `*_utils.py` names), they can be renamed with a follow-up change without impacting the public MCP tools. 

