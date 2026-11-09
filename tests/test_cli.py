from pathlib import Path

import pytest
from typer.testing import CliRunner

from fsaudit import cli, config

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "LOG_PATH", tmp_path / "test.log")
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.txt").write_text("hello")
    (data / "b.txt").write_text("hello")
    (data / "big.bin").write_bytes(b"0" * 5000)
    return data


def test_scan_then_analyses(workspace: Path) -> None:
    result = runner.invoke(cli.app, ["scan", str(workspace)])
    assert result.exit_code == 0
    assert "3 fichiers" in result.output

    result = runner.invoke(cli.app, ["dupes"])
    assert result.exit_code == 0
    assert "5.0 o" in result.output

    result = runner.invoke(cli.app, ["top", "-n", "1"])
    assert result.exit_code == 0
    assert "big.bin" in result.output

    result = runner.invoke(cli.app, ["ext"])
    assert result.exit_code == 0
    assert ".txt" in result.output

    result = runner.invoke(cli.app, ["scans"])
    assert result.exit_code == 0
    assert "Scans" in result.output


def test_analysis_without_scan_fails(workspace: Path) -> None:
    result = runner.invoke(cli.app, ["top"])
    assert result.exit_code == 1
    assert "Aucun scan" in result.output


def test_log_file_is_written(workspace: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    log = config.LOG_PATH.read_text(encoding="utf-8")
    assert "Début du scan" in log


def test_unknown_scan_fails(workspace: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    result = runner.invoke(cli.app, ["top", "--scan", "42"])
    assert result.exit_code == 1
    assert "Scan #42 introuvable" in result.output


def test_top_rejects_negative_limit(workspace: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    result = runner.invoke(cli.app, ["top", "-n", "-1"])
    assert result.exit_code == 2


def test_backup_command(workspace: Path, tmp_path: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    dest = tmp_path / "save"
    result = runner.invoke(cli.app, ["backup", str(dest)])
    assert result.exit_code == 0
    assert "3 copiés" in result.output
    result = runner.invoke(cli.app, ["backup", str(dest)])
    assert "3 déjà à jour" in result.output


def test_backup_refuses_dest_inside_source(workspace: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    result = runner.invoke(cli.app, ["backup", str(workspace / "save")])
    assert result.exit_code == 1
