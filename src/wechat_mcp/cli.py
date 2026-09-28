"""
Command line front end for the WeChat automation, meant for shell scripts
and skills (for example the ``wechat-automation`` Claude skill).

Every subcommand prints one JSON document on stdout and exits non-zero
when the operation failed (``error`` in the result, or ``sent`` false).
Use ``--text`` for a human readable rendering.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from .logging_config import logger


def _quiet_console(verbose: bool) -> None:
    """Keep stdout clean: only warnings on the console unless -v."""
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handler.setLevel(logging.INFO if verbose else logging.WARNING)


def _failed(result: Any) -> bool:
    if isinstance(result, dict):
        if result.get("error"):
            return True
        if "sent" in result and result.get("sent") is False and result.get("reply_message"):
            return True
        return False
    if isinstance(result, list):
        return any(isinstance(row, dict) and row.get("error") for row in result)
    return False


def _render_text(command: str, result: Any) -> str:
    lines: list[str] = []
    if isinstance(result, list):
        for row in result:
            if "warnings" in row and len(row) == 1:
                lines.extend(f"! {w}" for w in row["warnings"])
                continue
            if row.get("error"):
                lines.append(f"ERROR: {row['error']}")
                cands = row.get("candidates") or {}
                for section, names in cands.items():
                    if names:
                        lines.append(f"  {section}: {', '.join(names)}")
                continue
            sender = row.get("sender", "?")
            if sender == "SYSTEM":
                lines.append(f"--- {row.get('text', '')}")
                continue
            who = row.get("sender_name") or ("me" if sender == "ME" else sender.lower())
            kind = row.get("kind", "text")
            text = row.get("text", "").replace("\n", " | ")
            suffix = f" [{kind}]" if kind not in ("text",) else ""
            lines.append(f"[{who}]{suffix} {text}")
        return "\n".join(lines)

    if not isinstance(result, dict):
        return str(result)

    if command == "chats":
        for chat in result.get("chats", []):
            mute = " (muted)" if chat.get("muted") else ""
            preview = (chat.get("preview") or "").replace("\n", " ")
            lines.append(f"{chat.get('time') or '':>10}  {chat['name']}{mute}: {preview}")
        if result.get("current_chat"):
            lines.append(f"current chat: {result['current_chat']}")
    elif command == "check":
        version = result.get("version", {})
        lines.append(
            f"WeChat installed={version.get('installed_version')} "
            f"running={version.get('running_version')} status={version.get('status')}"
        )
        ui = result.get("ui", {})
        lines.append(f"UI probe ok={ui.get('ok')} missing={[m['element'] for m in ui.get('missing', [])]}")
        lines.append(f"compatible={result.get('compatible')}")
    elif result.get("error"):
        lines.append(f"ERROR: {result['error']}")
        for hint in (result.get("diagnostics") or {}).get("hints", []):
            lines.append(f"  hint: {hint}")
    else:
        for key, value in result.items():
            if key in ("warnings",):
                continue
            lines.append(f"{key}: {value}")
    for warning in result.get("warnings", []) if isinstance(result, dict) else []:
        lines.append(f"! {warning}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat-cli",
        description="Drive WeChat for Mac from the command line (JSON output).",
    )
    parser.add_argument("--text", action="store_true", help="human readable output")
    parser.add_argument("-v", "--verbose", action="store_true", help="show info logs")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="fetch recent messages of a chat")
    p.add_argument("chat")
    p.add_argument("-n", "--last", type=int, default=20)

    p = sub.add_parser("send", help="send a message to a chat")
    p.add_argument("chat")
    p.add_argument("message", nargs="*", help="message text (or use --stdin)")
    p.add_argument("--stdin", action="store_true", help="read the message from stdin")

    p = sub.add_parser("open", help="open a chat without sending")
    p.add_argument("chat")

    p = sub.add_parser("chats", help="list sidebar chats")
    p.add_argument("--max", type=int, default=30)
    p.add_argument("--no-scroll", action="store_true", help="only rows currently on screen")

    sub.add_parser("current", help="name of the open chat")
    sub.add_parser("check", help="WeChat version / UI compatibility report")

    p = sub.add_parser("moment", help="publish a text-only Moments post")
    p.add_argument("content", nargs="+")
    p.add_argument("--draft", action="store_true", help="fill the composer but do not post")

    p = sub.add_parser("add-contact", help="send a friend request by WeChat ID")
    p.add_argument("wechat_id")
    p.add_argument("--message", dest="friending_msg")
    p.add_argument("--remark")
    p.add_argument("--privacy", choices=["all", "chats_only"], default="all")
    p.add_argument("--hide-my-posts", action="store_true")
    p.add_argument("--hide-their-posts", action="store_true")
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _quiet_console(args.verbose)

    # Imported here so --help works without WeChat / pyobjc being usable.
    from . import mcp_server as server

    result: Any
    if args.command == "fetch":
        result = server.fetch_messages_by_chat(args.chat, last_n=args.last)
    elif args.command == "send":
        message = sys.stdin.read() if args.stdin else " ".join(args.message)
        if not message.strip():
            print(json.dumps({"error": "empty message"}))
            return 2
        result = server.reply_to_messages_by_chat(args.chat, message)
    elif args.command == "open":
        result = server.reply_to_messages_by_chat(args.chat, None)
    elif args.command == "chats":
        result = server.list_chats(max_chats=args.max, scroll=not args.no_scroll)
    elif args.command == "current":
        from .wechat_accessibility import get_current_chat_name, get_wechat_ax_app

        result = {"current_chat": get_current_chat_name(get_wechat_ax_app(activate=False))}
    elif args.command == "check":
        result = server.check_wechat_compatibility(refresh=True)
    elif args.command == "moment":
        result = server.publish_moment_without_media(" ".join(args.content), publish=not args.draft)
    elif args.command == "add-contact":
        result = server.add_contact_by_wechat_id(
            args.wechat_id,
            friending_msg=args.friending_msg,
            remark=args.remark,
            privacy=args.privacy,
            hide_my_posts=args.hide_my_posts,
            hide_their_posts=args.hide_their_posts,
        )
    else:  # pragma: no cover
        return 2

    if args.text:
        print(_render_text(args.command, result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if _failed(result) else 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
