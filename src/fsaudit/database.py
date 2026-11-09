import sqlite3
from collections.abc import Iterable
from dataclasses import astuple
from datetime import UTC, datetime
from pathlib import Path

from fsaudit.models import FileInfo

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY,
    root TEXT NOT NULL,
    scanned_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES scans(id),
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    size INTEGER NOT NULL,
    modified TEXT NOT NULL,
    extension TEXT NOT NULL,
    mime TEXT NOT NULL,
    hash TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def create_scan(conn: sqlite3.Connection, root: Path) -> int:
    row = conn.execute(
        "INSERT INTO scans (root, scanned_at) VALUES (?, ?) RETURNING id",
        (str(root), datetime.now(UTC).isoformat()),
    ).fetchone()
    conn.commit()
    return int(row["id"])


def insert_files(conn: sqlite3.Connection, scan_id: int, files: Iterable[FileInfo]) -> int:
    rows = [(scan_id, *astuple(file)) for file in files]
    conn.executemany(
        "INSERT INTO files (scan_id, path, name, size, modified, extension, mime, hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def list_scans(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()


def latest_scan_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT id FROM scans ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return int(row["id"])


def files_of_scan(conn: sqlite3.Connection, scan_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM files WHERE scan_id = ?", (scan_id,)).fetchall()
