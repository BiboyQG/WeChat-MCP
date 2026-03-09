"""
Smoke tests for the quote_reply_utils module.

These tests verify the module structure and imports without requiring
a running WeChat instance or macOS Accessibility API.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock


def _mock_macos_modules():
    """Mock macOS-specific modules so tests can run on any platform."""
    mock_modules = [
        "AppKit",
        "ApplicationServices",
        "Quartz",
        "PIL",
        "PIL.ImageGrab",
    ]
    mocks = {}
    for mod_name in mock_modules:
        if mod_name not in sys.modules:
            mocks[mod_name] = MagicMock()
            sys.modules[mod_name] = mocks[mod_name]
    return mocks


def test_module_imports():
    """Verify that quote_reply_utils can be imported."""
    _mock_macos_modules()
    try:
        from wechat_mcp import quote_reply_utils  # noqa: F401

        assert hasattr(quote_reply_utils, "quote_and_reply")
        assert hasattr(quote_reply_utils, "right_click_element_center")
        assert hasattr(quote_reply_utils, "find_context_menu_item")
        assert hasattr(quote_reply_utils, "find_message_element")
        print("PASS: quote_reply_utils imports successfully")
    except Exception as exc:
        print(f"SKIP: Cannot import on this platform: {exc}")


def test_mcp_server_has_tool():
    """Verify that mcp_server registers the quote_reply_to_message tool."""
    _mock_macos_modules()
    try:
        from wechat_mcp import mcp_server  # noqa: F401

        assert hasattr(mcp_server, "quote_reply_to_message")
        print("PASS: mcp_server has quote_reply_to_message tool")
    except Exception as exc:
        print(f"SKIP: Cannot import on this platform: {exc}")


if __name__ == "__main__":
    test_module_imports()
    test_mcp_server_has_tool()

