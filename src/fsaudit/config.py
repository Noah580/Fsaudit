import os
from pathlib import Path

from dotenv import load_dotenv

# Lit le fichier .env (s'il existe) et copie ses lignes dans les variables d'environnement.
load_dotenv()

# Chaque réglage est lu avec os.environ.get(clé, défaut) :
# si la variable n'est pas définie, la valeur par défaut est utilisée.
# L'outil fonctionne donc même sans fichier .env.
DB_PATH = Path(os.environ.get("FSAUDIT_DB", "fsaudit.db"))
LOG_PATH = Path(os.environ.get("FSAUDIT_LOG", "fsaudit.log"))
LOG_LEVEL = os.environ.get("FSAUDIT_LOG_LEVEL", "INFO")

# Une seule chaîne ".git,.venv" -> une liste [".git", ".venv"] grâce à split.
EXCLUDE = os.environ.get("FSAUDIT_EXCLUDE", ".git,__pycache__,.venv").split(",")
