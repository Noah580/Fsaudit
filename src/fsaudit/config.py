import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DB_PATH = Path(os.environ.get("FSAUDIT_DB", "fsaudit.db"))
LOG_PATH = Path(os.environ.get("FSAUDIT_LOG", "fsaudit.log"))
LOG_LEVEL = os.environ.get("FSAUDIT_LOG_LEVEL", "INFO")
EXCLUDE = os.environ.get("FSAUDIT_EXCLUDE", ".git,__pycache__,.venv").split(",")
