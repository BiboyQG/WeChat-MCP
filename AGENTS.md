# Repository Guidelines

## Project Structure & Modules
- Core code lives in `src/wechat_mcp` (MCP server, accessibility helpers, logging).
- Entry point is `wechat_mcp.mcp_server:main`, exposed as the `wechat-mcp` script.
- Logs are written under `logs/` by default (configurable via `WECHAT_MCP_LOG_DIR`).
- Keep macOS Accessibility and WeChat-specific logic in `wechat_accessibility.py`.

## Build, Run & Development
- Install dependencies: `uv sync` from the repository root.
- Run the MCP server (stdio): `uv run wechat-mcp --transport stdio`.
- Run over HTTP/SSE: `uv run wechat-mcp --transport streamable-http --port 3001` or `--transport sse`.
- Enable protocol debugging: `uv run wechat-mcp --mcp-debug --transport stdio`.

## Coding Style & Naming
- Python 3.12+, PEP 8 style, 4-space indentation, type hints where practical.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and relative imports within `wechat_mcp`.
- Prefer structured logging via `logging_config.logger`; avoid `print` for runtime behavior.
- Keep functions small, with clear docstrings explaining interaction with macOS Accessibility APIs.

## Testing Guidelines
- No formal automated test suite yet; new tests should use `pytest` under `tests/` mirroring `src/wechat_mcp`.
- Name test files `test_*.py` and test functions `test_*`.
- Run tests with `uv run pytest`.
- Avoid hitting real Accessibility APIs in unit tests; isolate them behind helper functions and use fakes where possible.

## Commit & Pull Request Guidelines
- Follow Conventional Commit style seen in history (e.g., `feat:`, `docs:`, `refactor(scope):`).
- Keep commits focused and descriptive; explain behavior changes, not just code moves.
- PRs should include: summary, motivation, how to reproduce/verify, and any macOS/WeChat version specifics.
- Attach relevant log snippets from `logs/wechat_mcp.log` when debugging Accessibility issues.

## Agent-Specific Instructions
- Keep diffs minimal and localized; avoid large refactors unless explicitly requested.
- Preserve existing logging, error handling, and transport behavior when extending features.
- Update `README.md` and this file when adding new tools, transports, or configuration knobs.
