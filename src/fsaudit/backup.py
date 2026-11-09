import logging
import shutil
import sqlite3
from pathlib import Path

from fsaudit.database import files_of_scan
from fsaudit.scanner import hash_file

logger = logging.getLogger(__name__)


def backup(conn: sqlite3.Connection, scan_id: int, source: Path, dest: Path) -> tuple[int, int]:
    copied = skipped = 0
    for row in files_of_scan(conn, scan_id):
        target = dest / row["path"]
        try:
            if target.is_file() and hash_file(target) == row["hash"]:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / row["path"], target)
            copied += 1
        except OSError as error:
            logger.warning("Copie impossible %s : %s", row["path"], error.strerror)
    return copied, skipped
