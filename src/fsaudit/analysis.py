import sqlite3
from dataclasses import dataclass, field

from fsaudit.database import files_of_scan


@dataclass
class Diff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    moved: list[tuple[str, str]] = field(default_factory=list)


def duplicates(conn: sqlite3.Connection, scan_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT hash, size, COUNT(*) AS copies, GROUP_CONCAT(path, ' | ') AS paths"
        " FROM files WHERE scan_id = ?"
        " GROUP BY hash HAVING COUNT(*) > 1"
        " ORDER BY size * (COUNT(*) - 1) DESC",
        (scan_id,),
    ).fetchall()


def biggest(conn: sqlite3.Connection, scan_id: int, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT path, size, mime FROM files WHERE scan_id = ? ORDER BY size DESC LIMIT ?",
        (scan_id, limit),
    ).fetchall()


def by_extension(conn: sqlite3.Connection, scan_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT extension, COUNT(*) AS count, SUM(size) AS total"
        " FROM files WHERE scan_id = ?"
        " GROUP BY extension ORDER BY total DESC",
        (scan_id,),
    ).fetchall()


def diff(conn: sqlite3.Connection, old_id: int, new_id: int) -> Diff:
    old = {row["path"]: row["hash"] for row in files_of_scan(conn, old_id)}
    new = {row["path"]: row["hash"] for row in files_of_scan(conn, new_id)}
    result = Diff()
    for path in sorted(old.keys() & new.keys()):
        if old[path] != new[path]:
            result.modified.append(path)
    removed_by_hash = {old[path]: path for path in old.keys() - new.keys()}
    for path in sorted(new.keys() - old.keys()):
        old_path = removed_by_hash.pop(new[path], None)
        if old_path is None:
            result.added.append(path)
        else:
            result.moved.append((old_path, path))
    result.removed = sorted(removed_by_hash.values())
    return result
