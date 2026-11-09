import hashlib
import logging
import mimetypes
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

from fsaudit.models import FileInfo

logger = logging.getLogger(__name__)


def matches(name: str, patterns: list[str]) -> bool:
    return any(fnmatch(name, pattern) for pattern in patterns)


def hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def inspect_file(path: Path, root: Path) -> FileInfo:
    stat = path.stat()
    mime, _ = mimetypes.guess_type(path.name)
    return FileInfo(
        path=path.relative_to(root).as_posix(),
        name=path.name,
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        extension=path.suffix.lower(),
        mime=mime or "unknown",
        hash=hash_file(path),
    )


def log_walk_error(error: OSError) -> None:
    logger.warning("Dossier inaccessible %s : %s", error.filename, error.strerror)


def scan(root: Path, exclude: list[str], include: list[str]) -> Iterator[FileInfo]:
    logger.info("Début du scan de %s", root)
    for dirpath, dirnames, filenames in os.walk(root, onerror=log_walk_error):
        dirnames[:] = [name for name in dirnames if not matches(name, exclude)]
        for filename in filenames:
            if matches(filename, exclude):
                continue
            if include and not matches(filename, include):
                continue
            path = Path(dirpath) / filename
            try:
                yield inspect_file(path, root)
            except OSError as error:
                logger.warning("Fichier ignoré %s : %s", path, error.strerror)
    logger.info("Fin du scan de %s", root)
