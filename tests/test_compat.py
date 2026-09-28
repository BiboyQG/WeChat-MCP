from __future__ import annotations

from pathlib import Path

from wechat_mcp import compat


def _patch_versions(monkeypatch, installed, running, acknowledged=""):
    def read(path: Path):
        return {"installed": installed, "running": running}[path.name]

    monkeypatch.setattr(compat, "_read_bundle_version", read)
    monkeypatch.setattr(compat, "get_installed_wechat_bundle", lambda: Path("installed"))
    monkeypatch.setattr(
        compat, "get_running_wechat_bundle", lambda: Path("running") if running else None
    )
    monkeypatch.setenv(compat.ENV_ACKNOWLEDGED_VERSIONS, acknowledged)
    monkeypatch.setattr(compat, "TESTED_WECHAT_VERSIONS", ("4.1.13",))
    monkeypatch.setattr(compat, "TESTED_WECHAT_SERIES", ("4.1",))


def test_tested_version_has_no_warnings(monkeypatch):
    _patch_versions(monkeypatch, ("4.1.13", "269602"), ("4.1.13", "269602"))
    info = compat.get_version_info()
    assert info.status == "tested" and info.warnings == [] and not info.restart_required


def test_newer_version_is_flagged(monkeypatch):
    _patch_versions(monkeypatch, ("4.2.0", "300000"), ("4.2.0", "300000"))
    info = compat.get_version_info()
    assert info.status == "newer"
    assert any("newer than" in w for w in info.warnings)


def test_same_series_build_is_soft_warning(monkeypatch):
    _patch_versions(monkeypatch, ("4.1.14", "270000"), ("4.1.14", "270000"))
    info = compat.get_version_info()
    assert info.status == "same_series"
    assert any("new build" in w for w in info.warnings)


def test_older_version_is_flagged(monkeypatch):
    _patch_versions(monkeypatch, ("3.8.7", "1"), ("3.8.7", "1"))
    assert compat.get_version_info().status == "older"


def test_update_pending_restart_detected(monkeypatch):
    _patch_versions(monkeypatch, ("4.2.0", "300000"), ("4.1.13", "269602"))
    info = compat.get_version_info()
    assert info.restart_required
    assert any("restart WeChat" in w for w in info.warnings)


def test_acknowledged_version_counts_as_tested(monkeypatch):
    _patch_versions(monkeypatch, ("4.2.0", "300000"), ("4.2.0", "300000"), acknowledged="4.2.0")
    assert compat.get_version_info().status == "tested"


def test_not_running_reports_installed_version(monkeypatch):
    _patch_versions(monkeypatch, ("4.1.13", "269602"), None)
    info = compat.get_version_info()
    assert not info.is_running and info.installed_version == "4.1.13" and info.status == "tested"


def test_compatibility_report_when_not_running(monkeypatch):
    _patch_versions(monkeypatch, ("4.1.13", "269602"), None)
    report = compat.compatibility_report()
    assert report["compatible"] is False
    assert report["ui"]["notes"] == ["WeChat is not running"]
