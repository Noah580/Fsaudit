import logging
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from fsaudit.database import files_of_scan
from fsaudit.scanner import hash_file

logger = logging.getLogger(__name__)


@dataclass
class BackupResult:
    copied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def is_up_to_date(target: Path, expected_hash: str) -> bool:
    return target.is_file() and hash_file(target) == expected_hash


def backup(conn: sqlite3.Connection, scan_id: int, source: Path, dest: Path) -> BackupResult:
    result = BackupResult()
    logger.info("Début du backup du scan #%s vers %s", scan_id, dest)
    for row in files_of_scan(conn, scan_id):
        path = row["path"]
        target = dest / path
        try:
            if is_up_to_date(target, row["hash"]):
                result.skipped.append(path)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / path, target)
            result.copied.append(path)
        except OSError as error:
            logger.warning("Copie impossible %s : %s", path, error.strerror)
            result.failed.append(path)
    logger.info("Fin du backup : %s copiés, %s à jour", len(result.copied), len(result.skipped))
    return result
