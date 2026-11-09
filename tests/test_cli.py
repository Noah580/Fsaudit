from pathlib import Path

import pytest
from typer.testing import CliRunner

from fsaudit import cli
from fsaudit.config import Settings

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings = Settings(tmp_path / "test.db", tmp_path / "test.log", "INFO", [".git"])
    monkeypatch.setattr(cli, "settings", settings)
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


def test_diff_between_two_scans(workspace: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    (workspace / "a.txt").unlink()
    (workspace / "c.txt").write_text("new")
    runner.invoke(cli.app, ["scan", str(workspace)])
    result = runner.invoke(cli.app, ["diff", "1", "2"])
    assert result.exit_code == 0
    assert "c.txt" in result.output
    assert "a.txt" in result.output


def test_analysis_without_scan_fails(workspace: Path) -> None:
    result = runner.invoke(cli.app, ["top"])
    assert result.exit_code == 1
    assert "Aucun scan" in result.output


def test_log_file_is_written(workspace: Path) -> None:
    runner.invoke(cli.app, ["scan", str(workspace)])
    log = cli.settings.log_path.read_text(encoding="utf-8")
    assert "Début du scan" in log
