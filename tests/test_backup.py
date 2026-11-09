import sqlite3
from pathlib import Path

import pytest

from fsaudit import database, scanner
from fsaudit.backup import backup


@pytest.fixture
def scanned(tmp_path: Path) -> tuple[sqlite3.Connection, int, Path]:
    source = tmp_path / "source"
    (source / "sub").mkdir(parents=True)
    (source / "a.txt").write_text("hello")
    (source / "sub" / "b.txt").write_text("world")
    conn = database.connect(tmp_path / "test.db")
    scan_id = database.create_scan(conn, source)
    database.insert_files(conn, scan_id, scanner.scan(source, [], []))
    return conn, scan_id, source


def test_backup_copies_all_files(
    scanned: tuple[sqlite3.Connection, int, Path], tmp_path: Path
) -> None:
    conn, scan_id, source = scanned
    dest = tmp_path / "dest"
    result = backup(conn, scan_id, source, dest)
    assert sorted(result.copied) == ["a.txt", "sub/b.txt"]
    assert (dest / "sub" / "b.txt").read_text() == "world"


def test_backup_skips_up_to_date_files(
    scanned: tuple[sqlite3.Connection, int, Path], tmp_path: Path
) -> None:
    conn, scan_id, source = scanned
    dest = tmp_path / "dest"
    backup(conn, scan_id, source, dest)
    (dest / "a.txt").write_text("changed in backup")
    result = backup(conn, scan_id, source, dest)
    assert result.copied == ["a.txt"]
    assert result.skipped == ["sub/b.txt"]
    assert (dest / "a.txt").read_text() == "hello"


def test_backup_continues_after_error(
    scanned: tuple[sqlite3.Connection, int, Path], tmp_path: Path
) -> None:
    conn, scan_id, source = scanned
    (source / "a.txt").unlink()
    result = backup(conn, scan_id, source, tmp_path / "dest")
    assert result.failed == ["a.txt"]
    assert result.copied == ["sub/b.txt"]
