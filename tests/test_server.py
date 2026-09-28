from __future__ import annotations

from wechat_mcp import mcp_server


def _quiet_focus(monkeypatch):
    monkeypatch.setattr(mcp_server, "get_mouse_location", lambda: (0.0, 0.0))
    monkeypatch.setattr(mcp_server, "move_mouse", lambda x, y: None)
    monkeypatch.setattr(mcp_server, "get_frontmost_bundle_id", lambda: "com.example.terminal")
    monkeypatch.setattr(mcp_server, "activate_bundle", lambda bundle_id: True)
    monkeypatch.setattr(mcp_server, "version_warnings", lambda: [])


def test_reply_does_not_send_when_chat_cannot_be_opened(monkeypatch):
    _quiet_focus(monkeypatch)
    monkeypatch.setattr(mcp_server, "get_current_chat_name", lambda: "Other")
    monkeypatch.setattr(
        mcp_server,
        "open_chat_for_contact",
        lambda name: {"error": "no exact match", "chat_name": name, "candidates": {}},
    )
    sent = []
    monkeypatch.setattr(mcp_server, "send_message", lambda text, expected_chat=None: sent.append(text))
    result = mcp_server.reply_to_messages_by_chat("Alice", "hi")
    assert result["sent"] is False and sent == []
    assert result["tool"] == "reply_to_messages_by_chat"


def test_reply_sends_with_expected_chat_guard(monkeypatch):
    _quiet_focus(monkeypatch)
    monkeypatch.setattr(mcp_server, "get_current_chat_name", lambda: "Alice")
    calls = []

    def fake_send(text, expected_chat=None):
        calls.append((text, expected_chat))
        return {"sent": True, "verified": True, "last_bubble": text}

    monkeypatch.setattr(mcp_server, "send_message", fake_send)
    result = mcp_server.reply_to_messages_by_chat("Alice", "hi")
    assert result["sent"] and result["verified"]
    assert calls == [("hi", "Alice")]


def test_reply_error_carries_diagnostics(monkeypatch):
    _quiet_focus(monkeypatch)
    monkeypatch.setattr(mcp_server, "get_current_chat_name", lambda: "Alice")

    def boom(text, expected_chat=None):
        raise RuntimeError("Refusing to send: the open chat is 'Bob', not 'Alice'")

    monkeypatch.setattr(mcp_server, "send_message", boom)
    monkeypatch.setattr(mcp_server, "failure_context", lambda exc: {"version_status": "tested"})
    result = mcp_server.reply_to_messages_by_chat("Alice", "hi")
    assert result["sent"] is False and "Refusing" in result["error"]
    assert result["diagnostics"]["version_status"] == "tested"


def test_fetch_prepends_version_warnings(monkeypatch):
    _quiet_focus(monkeypatch)
    monkeypatch.setattr(mcp_server, "version_warnings", lambda: ["WeChat 9.9 is newer"])
    monkeypatch.setattr(mcp_server, "get_current_chat_name", lambda: "Alice")
    monkeypatch.setattr(
        mcp_server,
        "fetch_recent_messages",
        lambda last_n: [mcp_server.ChatMessage("ME", "hi")],
    )
    rows = mcp_server.fetch_messages_by_chat("Alice", last_n=1)
    assert rows[0] == {"warnings": ["WeChat 9.9 is newer"]}
    assert rows[1]["text"] == "hi" and rows[1]["kind"] == "text"


def test_ui_session_restores_previous_app(monkeypatch):
    monkeypatch.setattr(mcp_server, "get_mouse_location", lambda: (0.0, 0.0))
    monkeypatch.setattr(mcp_server, "move_mouse", lambda x, y: None)
    state = {"front": "com.example.terminal"}
    monkeypatch.setattr(mcp_server, "get_frontmost_bundle_id", lambda: state["front"])
    restored = []

    def activate(bundle_id):
        restored.append(bundle_id)
        state["front"] = bundle_id
        return True

    monkeypatch.setattr(mcp_server, "activate_bundle", activate)
    with mcp_server.ui_session():
        state["front"] = mcp_server.WECHAT_BUNDLE_ID
    assert restored == ["com.example.terminal"]
