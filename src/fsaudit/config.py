import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    db_path: Path
    log_path: Path
    log_level: str
    exclude: list[str]


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        db_path=Path(os.environ.get("FSAUDIT_DB", "fsaudit.db")),
        log_path=Path(os.environ.get("FSAUDIT_LOG", "fsaudit.log")),
        log_level=os.environ.get("FSAUDIT_LOG_LEVEL", "INFO"),
        exclude=os.environ.get("FSAUDIT_EXCLUDE", ".git,__pycache__,.venv").split(","),
    )
