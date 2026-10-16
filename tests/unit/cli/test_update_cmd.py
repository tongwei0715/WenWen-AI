"""Tests for `wenwen update` (WenWen AI fork: tracks fork GitHub releases)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from octop.cli.main import cli
from octop.infra.setup import self_update


def _fork_release(tag: str) -> tuple[str, str, None]:
    return (tag, f"https://github.com/tongwei0715/WenWen-AI/releases/tag/{tag}", None)


def test_update_check_only_no_install(monkeypatch: pytest.MonkeyPatch) -> None:
    import octop.cli.commands.update as update_cmd

    monkeypatch.setattr(
        update_cmd,
        "fetch_fork_release",
        lambda: _fork_release("v1.0.2b7-wenwen.9"),
    )
    monkeypatch.setattr(update_cmd, "get_wenwen_version", lambda: "1.0.2b7-wenwen.8")
    monkeypatch.setattr(update_cmd, "is_source_install", lambda: False)

    called: dict[str, bool] = {}

    def _fake_upgrade(**kw):
        called["ran"] = True
        return self_update.UpgradeResult(success=True)

    monkeypatch.setattr(update_cmd, "run_upgrade", _fake_upgrade)

    runner = CliRunner()
    result = runner.invoke(cli, ["update", "--check"])
    assert result.exit_code == 0
    assert "1.0.2b7-wenwen.9" in result.output
    assert "ran" not in called


def test_update_yes_runs_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    import octop.cli.commands.update as update_cmd

    monkeypatch.setattr(
        update_cmd,
        "fetch_fork_release",
        lambda: _fork_release("v1.0.2b7-wenwen.9"),
    )
    monkeypatch.setattr(update_cmd, "get_wenwen_version", lambda: "1.0.2b7-wenwen.8")
    monkeypatch.setattr(update_cmd, "is_source_install", lambda: False)
    monkeypatch.setattr(
        update_cmd, "resolve_venv_python", lambda: "/home/user/.octop/venv/bin/python"
    )

    called: dict[str, bool] = {}

    def _fake_upgrade(**kw):
        called["ran"] = True
        called["kwargs"] = kw
        return self_update.UpgradeResult(success=True, installed_version="1.0.2b7-wenwen.9")

    monkeypatch.setattr(update_cmd, "run_upgrade", _fake_upgrade)

    runner = CliRunner()
    result = runner.invoke(cli, ["update", "--yes"])
    assert result.exit_code == 0
    assert called.get("ran") is True
    assert called["kwargs"]["version"] == "1.0.2b7-wenwen.9"
    assert "/home/user/.octop/venv/bin/python" in result.output


def test_update_already_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    import octop.cli.commands.update as update_cmd

    monkeypatch.setattr(
        update_cmd,
        "fetch_fork_release",
        lambda: _fork_release("v1.0.2b7-wenwen.8"),
    )
    monkeypatch.setattr(update_cmd, "get_wenwen_version", lambda: "1.0.2b7-wenwen.8")
    monkeypatch.setattr(update_cmd, "is_source_install", lambda: False)

    runner = CliRunner()
    result = runner.invoke(cli, ["update", "--check"])
    assert result.exit_code == 0
    assert "up to date" in result.output.lower()


def test_build_upgrade_command_uses_managed_venv_python() -> None:
    python = "/home/user/.octop/venv/bin/python"
    cmd = self_update.build_upgrade_command("uv", python, index_url="https://mirror.example/simple")
    assert cmd is not None
    assert "--python" in cmd
    assert python in cmd
    assert "--upgrade-package" in cmd
    assert "wenwen-ai" in cmd
    assert "https://mirror.example/simple" in cmd
    assert "--target" not in cmd


def test_build_upgrade_command_pins_version() -> None:
    python = "/home/user/.octop/venv/bin/python"
    cmd = self_update.build_upgrade_command("uv", python, version="1.0.2b7-wenwen.9")
    assert cmd is not None
    # Fork installs come from the fork's GitHub repo, never PyPI.
    assert any("wenwen-ai @ git+https://github.com/" in arg for arg in cmd)
    assert any("@v1.0.2b7-wenwen.9" in arg for arg in cmd)
    assert "--prerelease" not in cmd


def test_build_upgrade_command_green_packages_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    packages = tmp_path / "packages"
    packages.mkdir()
    monkeypatch.setenv("OCTOP_GREEN_PACKAGES", str(packages))
    python = "/opt/octop/runtime/bin/python3"
    cmd = self_update.build_upgrade_command("uv", python)
    assert cmd is not None
    assert "--target" in cmd
    assert str(packages) in cmd


def test_resolve_venv_python_green_uses_current_interpreter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    packages = tmp_path / "packages"
    packages.mkdir()
    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("OCTOP_HOME", str(tmp_path))
    monkeypatch.setenv("OCTOP_GREEN_PACKAGES", str(packages))
    monkeypatch.setattr(self_update.sys, "executable", "/bundled/python3")
    monkeypatch.setattr(self_update.sys, "prefix", "/usr")
    monkeypatch.setattr(self_update.sys, "base_prefix", "/usr")
    assert self_update.resolve_venv_python() == "/bundled/python3"


def test_resolve_venv_python_prefers_octop_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setenv("OCTOP_HOME", str(tmp_path))
    monkeypatch.setattr(self_update.sys, "prefix", "/usr")
    monkeypatch.setattr(self_update.sys, "base_prefix", "/usr")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    assert self_update.resolve_venv_python() == str(venv_python)


def test_update_source_install_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    import octop.cli.commands.update as update_cmd

    monkeypatch.setattr(
        update_cmd,
        "fetch_fork_release",
        lambda: _fork_release("v1.0.2b7-wenwen.9"),
    )
    monkeypatch.setattr(update_cmd, "get_wenwen_version", lambda: "1.0.2b7-wenwen.8")
    monkeypatch.setattr(update_cmd, "is_source_install", lambda: True)
    monkeypatch.setattr(update_cmd, "get_source_dir", lambda: "/src/wenwen-ai")
    monkeypatch.setattr(update_cmd, "get_editable_path", lambda: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["update", "--yes"])
    assert result.exit_code == 1
    assert "/src/wenwen-ai" in result.output
    assert "git pull" in result.output
