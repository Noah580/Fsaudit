import sqlite3
from pathlib import Path

import pytest

from fsaudit import analysis, database
from fsaudit.models import FileInfo


def info(path: str, size: int, content_hash: str) -> FileInfo:
    extension = Path(path).suffix
    return FileInfo(
        path, Path(path).name, size, "2026-01-01T00:00:00+00:00", extension, "x", content_hash
    )


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    return database.connect(tmp_path / "test.db")


def test_duplicates(conn: sqlite3.Connection) -> None:
    scan_id = database.create_scan(conn, Path("root"))
    database.insert_files(
        conn,
        scan_id,
        [info("a.txt", 100, "h1"), info("copy/a.txt", 100, "h1"), info("b.txt", 50, "h2")],
    )
    rows = analysis.duplicates(conn, scan_id)
    assert len(rows) == 1
    assert rows[0]["copies"] == 2
    assert rows[0]["size"] == 100


def test_biggest(conn: sqlite3.Connection) -> None:
    scan_id = database.create_scan(conn, Path("root"))
    database.insert_files(
        conn, scan_id, [info("small", 1, "a"), info("big", 300, "b"), info("mid", 20, "c")]
    )
    rows = analysis.biggest(conn, scan_id, 2)
    assert [row["path"] for row in rows] == ["big", "mid"]


def test_by_extension(conn: sqlite3.Connection) -> None:
    scan_id = database.create_scan(conn, Path("root"))
    database.insert_files(
        conn, scan_id, [info("a.py", 10, "a"), info("b.py", 30, "b"), info("c.txt", 5, "c")]
    )
    rows = analysis.by_extension(conn, scan_id)
    assert rows[0]["extension"] == ".py"
    assert rows[0]["count"] == 2
    assert rows[0]["total"] == 40


def test_latest_scan_id(conn: sqlite3.Connection) -> None:
    assert database.latest_scan_id(conn) is None
    database.create_scan(conn, Path("root"))
    second = database.create_scan(conn, Path("root"))
    assert database.latest_scan_id(conn) == second
