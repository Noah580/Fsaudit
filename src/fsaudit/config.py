# Le module os donne accès au système, et surtout à os.environ : le dictionnaire des
# variables d'environnement, c'est-à-dire les réglages que le terminal passe aux programmes.
import os

# Path est le type qui représente un chemin de fichier. On l'utilise pour que DB_PATH et
# LOG_PATH soient de vrais chemins et pas de simples textes.
from pathlib import Path

# On importe la seule fonction qu'on utilise de la librairie python-dotenv.
# Attention : on installe "python-dotenv" mais on importe "dotenv".
from dotenv import load_dotenv

# Cherche un fichier nommé .env dans le dossier courant. S'il existe, chaque ligne du type
# FSAUDIT_DB=fsaudit.db est ajoutée dans os.environ, comme si on avait défini la variable
# dans le terminal. S'il n'existe pas, la fonction ne fait rien et ne plante pas.
load_dotenv()

# os.environ.get("FSAUDIT_DB", "fsaudit.db") veut dire : « donne-moi la valeur de la variable
# FSAUDIT_DB, et si elle n'existe pas, donne-moi "fsaudit.db" ». C'est la méthode .get() des
# dictionnaires avec une valeur par défaut. Grâce à ce défaut, l'outil marche même sans .env.
# Path(...) transforme le texte en objet chemin.
DB_PATH = Path(os.environ.get("FSAUDIT_DB", "fsaudit.db"))
LOG_PATH = Path(os.environ.get("FSAUDIT_LOG", "fsaudit.log"))

# Le niveau de log reste un texte ("INFO" par défaut) car logging.basicConfig accepte
# directement le nom du niveau.
LOG_LEVEL = os.environ.get("FSAUDIT_LOG_LEVEL", "INFO")

# Dans le .env, les motifs à exclure sont sur une seule ligne séparés par des virgules.
# Le scanner a besoin d'une liste : .split(",") coupe la chaîne à chaque virgule et renvoie
# [".git", "__pycache__", ".venv"]. La CLI y ajoutera les motifs passés avec --exclude.
EXCLUDE = os.environ.get("FSAUDIT_EXCLUDE", ".git,__pycache__,.venv").split(",")

# Pourquoi des MAJUSCULES : en Python, un nom en majuscules signale une constante, une valeur
# fixée une fois au démarrage et qu'on ne modifie plus. Ces lignes s'exécutent une seule fois,
# quand cli.py fait "from fsaudit import config". Ensuite le programme lit config.DB_PATH.
