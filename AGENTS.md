# Repository Guidelines

## Project Structure & Modules
- Core code lives in `src/wechat_mcp` (MCP server, accessibility helpers, logging).
- Entry points: `wechat_mcp.mcp_server:main` (`wechat-mcp`, the MCP server) and `wechat_mcp.cli:main` (`wechat-cli`, used by the `wechat-automation` shell skill).
- Logs are written under `logs/` by default (configurable via `WECHAT_MCP_LOG_DIR`).
- Keep macOS Accessibility and WeChat-specific logic in `wechat_accessibility.py`; window capture and OCR live in `capture.py`; version/UI compatibility checks in `compat.py`.
- The code targets WeChat for Mac 4.x (Qt client). Identifiers it relies on: `session_list` / `session_item_<name>`, `search_list` / `search_item_<name>` (in a separate AXDialog), `current_chat_name_label`, `chat_message_list` / `chat_bubble_item_view`, `chat_input_field`, `sns_list` (Moments).
- After verifying a new WeChat release, add it to `TESTED_WECHAT_VERSIONS` in `compat.py`.

## Build, Run & Development
- Install dependencies: `uv sync` from the repository root.
- Run the MCP server (stdio): `uv run wechat-mcp --transport stdio`.
- Run over HTTP/SSE: `uv run wechat-mcp --transport streamable-http` or `--transport sse`.
- Enable protocol debugging: `uv run wechat-mcp --mcp-debug --transport stdio`.

## Coding Style & Naming
- Python 3.12+, PEP 8 style, 4-space indentation, type hints where practical.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and relative imports within `wechat_mcp`.
- Prefer structured logging via `logging_config.logger`; avoid `print` for runtime behavior.
- Keep functions small, with clear docstrings explaining interaction with macOS Accessibility APIs.

## Testing Guidelines
- Unit tests live under `tests/` and run without WeChat: `tests/conftest.py` provides a `FakeElement` tree wired into `ax_get`.
- Name test files `test_*.py` and test functions `test_*`; run with `uv run pytest`.
- Never write tests that message real contacts. For live checks use the "File Transfer" chat (your own device chat).

## Commit & Pull Request Guidelines
- Follow Conventional Commit style seen in history (e.g., `feat:`, `docs:`, `refactor(scope):`).
- Keep commits focused and descriptive; explain behavior changes, not just code moves.
- PRs should include: summary, motivation, how to reproduce/verify, and any macOS/WeChat version specifics.
- Attach relevant log snippets from `logs/wechat_mcp.log` when debugging Accessibility issues.

## Agent-Specific Instructions
- Keep diffs minimal and localized; avoid large refactors unless explicitly requested.
- Preserve existing logging, error handling, and transport behavior when extending features.
- Never type or press Return without first confirming, via Accessibility, which chat is open and that the text landed in `chat_input_field` (see `send_message`). Keyboard input into the wrong field sends messages to the wrong contact.
- Update `README.md` and this file when adding new tools, transports, or configuration knobs.
