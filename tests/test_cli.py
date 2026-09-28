from __future__ import annotations

from wechat_mcp import cli


def test_failed_detection():
    assert cli._failed({"error": "boom"})
    assert cli._failed({"sent": False, "reply_message": "hi"})
    assert not cli._failed({"sent": False, "reply_message": None})  # plain "open"
    assert not cli._failed({"sent": True})
    assert cli._failed([{"error": "no match"}])
    assert not cli._failed([{"sender": "ME", "text": "x"}])


def test_render_messages_text():
    rows = [
        {"warnings": ["WeChat 9.9 is newer"]},
        {"sender": "SYSTEM", "text": "16:10", "kind": "system", "sender_name": None},
        {"sender": "OTHER", "text": "hi", "kind": "text", "sender_name": "Bob"},
        {"sender": "ME", "text": "File\nreport.pdf", "kind": "file", "sender_name": None},
    ]
    out = cli._render_text("fetch", rows)
    assert "! WeChat 9.9 is newer" in out
    assert "--- 16:10" in out
    assert "[Bob] hi" in out
    assert "[me] [file] File | report.pdf" in out


def test_render_chats_and_errors():
    out = cli._render_text(
        "chats",
        {"chats": [{"name": "Alice", "preview": "yo", "time": "16:00", "muted": True}], "current_chat": "Bob"},
    )
    assert "Alice (muted): yo" in out and "current chat: Bob" in out
    out = cli._render_text("send", {"error": "nope", "diagnostics": {"hints": ["update?"]}})
    assert out.startswith("ERROR: nope") and "hint: update?" in out


def test_parser_subcommands():
    args = cli.build_parser().parse_args(["--text", "send", "Alice", "hello", "world"])
    assert args.command == "send" and args.message == ["hello", "world"] and args.text
    args = cli.build_parser().parse_args(["chats", "--no-scroll", "--max", "5"])
    assert args.no_scroll and args.max == 5
