"""
WeChat version and UI compatibility checks.

The MCP server drives WeChat through Accessibility identifiers that Tencent
can change between releases. This module

- reads the installed and the currently running WeChat version,
- compares them with the versions this code base was verified against,
- probes the main window for the identifiers the tools rely on,

so that tools can warn the caller when WeChat was updated (and, when the
update broke an identifier, say which one).
"""

from __future__ import annotations

import os
import plistlib
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import AppKit
from ApplicationServices import kAXTextAreaRole

from .logging_config import logger

WECHAT_BUNDLE_ID = "com.tencent.xinWeChat"

#: WeChat for Mac versions the Accessibility flows were verified against.
#: Extend this list after re-testing a new release (see docs/detailed-guide.md).
TESTED_WECHAT_VERSIONS: tuple[str, ...] = ("4.1.13",)

#: Major.minor series that share the same UI structure as the tested builds.
TESTED_WECHAT_SERIES: tuple[str, ...] = ("4.1",)

#: Environment variable listing extra versions to treat as verified
#: (comma separated), e.g. after a manual check of a newer build.
ENV_ACKNOWLEDGED_VERSIONS = "WECHAT_MCP_ACKNOWLEDGED_VERSIONS"

#: Accessibility identifiers / titles the tools depend on, with the tool that
#: needs each one. Probed on the Chats tab of the main window.
REQUIRED_UI_ELEMENTS: dict[str, str] = {
    "session_list": "list_chats / opening chats from the sidebar",
    "search_field": "opening chats via search / add_contact_by_wechat_id",
    "chat_message_list": "fetch_messages_by_chat",
    "chat_input_field": "reply_to_messages_by_chat",
    "current_chat_name_label": "detecting the open chat",
}

_PROBE_TTL_SECONDS = 300.0


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _read_bundle_version(bundle_path: Path) -> tuple[str | None, str | None]:
    plist_path = bundle_path / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as fh:
            info = plistlib.load(fh)
    except (OSError, plistlib.InvalidFileException) as exc:
        logger.debug("Could not read %s: %s", plist_path, exc)
        return None, None
    return info.get("CFBundleShortVersionString"), info.get("CFBundleVersion")


def get_installed_wechat_bundle() -> Path | None:
    """Path of the WeChat app bundle as resolved by LaunchServices."""
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    url = workspace.URLForApplicationWithBundleIdentifier_(WECHAT_BUNDLE_ID)
    if url is not None:
        return Path(url.path())
    for candidate in ("/Applications/WeChat.app", "/Applications/微信.app"):
        if Path(candidate).exists():
            return Path(candidate)
    return None


def get_running_wechat_bundle() -> Path | None:
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        WECHAT_BUNDLE_ID
    )
    if not apps:
        return None
    url = apps[0].bundleURL()
    return Path(url.path()) if url is not None else None


@dataclass
class VersionInfo:
    installed_version: str | None = None
    installed_build: str | None = None
    running_version: str | None = None
    running_build: str | None = None
    is_running: bool = False
    tested_versions: tuple[str, ...] = TESTED_WECHAT_VERSIONS
    #: "tested" | "same_series" | "newer" | "older" | "unknown"
    status: str = "unknown"
    restart_required: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tested_versions"] = list(self.tested_versions)
        return data


def _acknowledged_versions() -> set[str]:
    raw = os.getenv(ENV_ACKNOWLEDGED_VERSIONS, "")
    return {v.strip() for v in raw.split(",") if v.strip()}


def get_version_info() -> VersionInfo:
    """Collect installed/running WeChat versions and classify them."""
    info = VersionInfo()

    installed = get_installed_wechat_bundle()
    if installed is not None:
        info.installed_version, info.installed_build = _read_bundle_version(installed)

    running = get_running_wechat_bundle()
    info.is_running = running is not None
    if running is not None:
        info.running_version, info.running_build = _read_bundle_version(running)

    effective = info.running_version or info.installed_version
    if effective is None:
        info.status = "unknown"
        info.warnings.append("Could not determine the WeChat version (is WeChat installed?).")
        return info

    verified = set(TESTED_WECHAT_VERSIONS) | _acknowledged_versions()
    newest_tested = max(TESTED_WECHAT_VERSIONS, key=_version_tuple)

    if effective in verified:
        info.status = "tested"
    elif any(effective.startswith(series + ".") for series in TESTED_WECHAT_SERIES):
        info.status = "same_series"
    elif _version_tuple(effective) > _version_tuple(newest_tested):
        info.status = "newer"
    else:
        info.status = "older"

    if info.status == "newer":
        info.warnings.append(
            f"WeChat {effective} is newer than the versions this server was verified "
            f"against ({', '.join(TESTED_WECHAT_VERSIONS)}). The UI may have changed; "
            "if a tool fails, run check_wechat_compatibility and re-verify the flows."
        )
    elif info.status == "older":
        info.warnings.append(
            f"WeChat {effective} is older than the verified versions "
            f"({', '.join(TESTED_WECHAT_VERSIONS)}); WeChat 3.x has a different UI."
        )
    elif info.status == "same_series":
        info.warnings.append(
            f"WeChat {effective} is a new build in the verified {effective.rsplit('.', 1)[0]} "
            "series; minor UI changes are possible."
        )

    if (
        info.is_running
        and info.installed_version
        and info.running_version
        and (info.installed_version, info.installed_build)
        != (info.running_version, info.running_build)
    ):
        info.restart_required = True
        info.warnings.append(
            f"WeChat {info.installed_version} is installed but {info.running_version} "
            "is still running; restart WeChat to use the new version."
        )

    return info


@dataclass
class UIProbe:
    checked_at: float
    found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "found": list(self.found),
            "missing": [
                {"element": name, "needed_for": REQUIRED_UI_ELEMENTS.get(name, "")}
                for name in self.missing
            ],
            "notes": list(self.notes),
        }


_probe_cache: UIProbe | None = None


def probe_ui(ax_app: Any | None = None, force: bool = False) -> UIProbe:
    """
    Check that the Accessibility identifiers the tools depend on are
    present in the main window. Results are cached for a few minutes.
    """
    global _probe_cache
    if (
        not force
        and _probe_cache is not None
        and time.time() - _probe_cache.checked_at < _PROBE_TTL_SECONDS
    ):
        return _probe_cache

    # Imported lazily to avoid an import cycle.
    from .wechat_accessibility import (
        SEARCH_FIELD_TITLES,
        dfs,
        ensure_chats_tab,
        find_by_identifier,
        get_wechat_ax_app,
    )

    probe = UIProbe(checked_at=time.time())
    try:
        if ax_app is None:
            ax_app = get_wechat_ax_app()
        main_window = ensure_chats_tab(ax_app)
    except Exception as exc:  # noqa: BLE001
        probe.missing = list(REQUIRED_UI_ELEMENTS)
        probe.notes.append(f"Could not inspect the main window: {exc}")
        _probe_cache = probe
        return probe

    for name in REQUIRED_UI_ELEMENTS:
        if name == "search_field":
            element = dfs(
                main_window,
                lambda el, role, title, ident: role == kAXTextAreaRole
                and title in SEARCH_FIELD_TITLES,
            )
        else:
            element = find_by_identifier(main_window, name)
        (probe.found if element is not None else probe.missing).append(name)

    chat_dependent = {"chat_message_list", "chat_input_field", "current_chat_name_label"}
    if chat_dependent & set(probe.missing) and not chat_dependent & set(probe.found):
        probe.notes.append(
            "No chat is open in WeChat; message list, input field and chat title "
            "only exist while a chat is selected."
        )

    if probe.missing:
        logger.warning("WeChat UI probe: missing %s", probe.missing)
    else:
        logger.info("WeChat UI probe: all %d required elements found", len(probe.found))
    _probe_cache = probe
    return probe


def invalidate_probe() -> None:
    global _probe_cache
    _probe_cache = None


def compatibility_report(ax_app: Any | None = None, force: bool = False) -> dict[str, Any]:
    """Full report combining version classification and the UI probe."""
    version = get_version_info()
    report: dict[str, Any] = {"version": version.to_dict()}
    if version.is_running:
        report["ui"] = probe_ui(ax_app, force=force).to_dict()
    else:
        report["ui"] = {"ok": False, "found": [], "missing": [], "notes": ["WeChat is not running"]}
    warnings = list(version.warnings)
    if version.is_running and not report["ui"]["ok"]:
        missing = ", ".join(m["element"] for m in report["ui"]["missing"])
        warnings.append(
            f"Required WeChat UI elements not found: {missing}. "
            "WeChat's Accessibility layout may have changed."
        )
    report["warnings"] = warnings
    report["compatible"] = version.status in ("tested", "same_series") and report["ui"]["ok"]
    return report


def version_warnings() -> list[str]:
    """Cheap per-call warnings (no Accessibility access)."""
    return get_version_info().warnings


def failure_context(exc: BaseException | None = None) -> dict[str, Any]:
    """
    Extra diagnostics attached to tool errors: the WeChat version status and
    a fresh UI probe, so the caller can tell a WeChat update from a
    transient failure.
    """
    version = get_version_info()
    context: dict[str, Any] = {
        "wechat_version": version.running_version or version.installed_version,
        "version_status": version.status,
        "tested_versions": list(TESTED_WECHAT_VERSIONS),
    }
    try:
        probe = probe_ui(force=True)
        context["ui_probe"] = probe.to_dict()
    except Exception as probe_exc:  # noqa: BLE001
        context["ui_probe"] = {"ok": False, "notes": [str(probe_exc)]}
    hints = list(version.warnings)
    if not context["ui_probe"].get("ok", False):
        hints.append(
            "One or more WeChat UI elements the server relies on were not found; "
            "this usually means WeChat was updated or no chat is open."
        )
    if hints:
        context["hints"] = hints
    return context
