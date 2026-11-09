import logging
from pathlib import Path


def setup_logging(log_path: Path, level: str) -> None:
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    log_file = logging.FileHandler(log_path, encoding="utf-8")
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
        handlers=[console, log_file],
        force=True,
    )
