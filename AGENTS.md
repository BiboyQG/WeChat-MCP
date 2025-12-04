# Repository Guidelines

## Project Structure & Module Organization

- `src/wechat_mcp/`: core MCP server (`mcp_server.py`), logging, and macOS Accessibility helpers.
- Root scripts (`list_chats.py`, `search_contacts.py`, `send_message.py`, `simple_sender_detection.py`): small CLIs that should delegate to functions in `wechat_mcp`.
- `logs/`: rotating runtime logs (typically `logs/wechat_mcp.log`); useful for debugging but not for long-term storage.
- Future tests should live under `tests/` mirroring package paths, e.g. `tests/wechat_mcp/test_mcp_server.py`.

## Build, Test, and Development Commands

- Create/sync environment: `uv sync` (from the repository root).
- Run MCP server: `uv run wechat-mcp --transport stdio` (add `--mcp-debug` while developing).
- Run helper scripts, e.g.: `uv run python list_chats.py`.
- Run tests (once added): `uv run pytest`.
- Prefer `uv run ...` over manually activating the virtual environment.

## Coding Style & Naming Conventions

- Python 3.12+, PEP 8 style, 4-space indentation.
- Package/modules: `snake_case` (e.g. `wechat_accessibility.py`).
- Functions/variables: `snake_case`; classes: `CamelCase`; constants: `UPPER_SNAKE_CASE`.
- Use type hints and concise docstrings for public functions, especially under `src/wechat_mcp/`.
- Keep business logic inside `src/wechat_mcp`; root scripts should remain thin wrappers.

## Testing Guidelines

- Tests are currently minimal; add new tests under `tests/` using `pytest`.
- Name test files `test_*.py` and mirror the target module path.
- Prefer fast, isolated tests; mock external APIs and macOS-specific integrations.
- Document new test helpers so they can be reused across modules.

## Commit & Pull Request Guidelines

- Follow a Conventional Commits style: `type(scope): summary`, e.g. `docs(README.md): clarify uv usage` or `feat(wechat_accessibility): improve sender detection`.
- Keep commits focused, logically grouped, and avoid large reformatting-only changes.
- PRs should include: a clear summary, motivation, any user-visible changes, and the exact commands you ran (e.g. `uv run pytest`, `uv run wechat-mcp --mcp-debug`).

## Security & Configuration Tips

- Do not commit API keys, tokens, or `.env` files; configure providers via `WECHAT_MCP_*` environment variables.
- Logs in `logs/` may include chat metadata; avoid sharing them publicly.
- macOS Accessibility permissions are required for WeChat automation—document any troubleshooting steps you discover in `README.md`.

