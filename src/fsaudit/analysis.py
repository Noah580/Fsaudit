import sqlite3


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
