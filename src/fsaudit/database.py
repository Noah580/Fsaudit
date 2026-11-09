# sqlite3 est inclus dans Python : la base est un simple fichier, pas de serveur à installer.
import sqlite3

# Iterable sert au typage : insert_files accepte « n'importe quoi qu'on peut parcourir »,
# donc aussi bien une liste qu'un générateur (celui de scanner.scan).
from collections.abc import Iterable

# astuple transforme une dataclass en tuple de ses valeurs, dans l'ordre des champs.
from dataclasses import astuple
from datetime import UTC, datetime
from pathlib import Path

from fsaudit.models import FileInfo

# Le schéma : la description des tables. Deux tables :
# - scans : une ligne par lancement de « fsaudit scan » (quel dossier, quand). C'est
#   l'historique. Garder plusieurs scans permet de faire un diff entre deux d'entre eux.
# - files : une ligne par fichier trouvé. scan_id dit à quel scan la ligne appartient
#   (REFERENCES scans(id) = clé étrangère vers la table scans).
# INTEGER PRIMARY KEY : identifiant unique attribué automatiquement (1, 2, 3…).
# NOT NULL : la colonne doit toujours avoir une valeur.
# IF NOT EXISTS : si la table existe déjà, la commande ne fait rien et ne plante pas,
# donc on peut exécuter ce schéma à chaque lancement.
SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY,
    root TEXT NOT NULL,
    scanned_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES scans(id),
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    size INTEGER NOT NULL,
    modified TEXT NOT NULL,
    extension TEXT NOT NULL,
    mime TEXT NOT NULL,
    hash TEXT NOT NULL
);
"""


# Ouvre la base et la prépare. Appelée au début de chaque commande de la CLI.
def connect(db_path: Path) -> sqlite3.Connection:
    # Ouvre le fichier, ou le crée s'il n'existe pas encore.
    conn = sqlite3.connect(db_path)
    # Par défaut une ligne lue est un tuple : row[3]. Avec Row, on écrit row["size"] :
    # beaucoup plus lisible, c'est ce que fait la CLI.
    conn.row_factory = sqlite3.Row
    # executescript exécute plusieurs instructions SQL d'un coup (nos deux CREATE TABLE).
    conn.executescript(SCHEMA)
    return conn


# Enregistre un nouveau scan et renvoie son numéro (l'id que la CLI affiche : « Scan #2 »).
def create_scan(conn: sqlite3.Connection, root: Path) -> int:
    # Les ? sont des paramètres : SQLite les remplace par les valeurs du tuple juste après,
    # en les échappant. C'est une requête PARAMÉTRÉE : on ne construit jamais une requête
    # avec une f-string, c'est la protection de base contre l'injection SQL (un nom de
    # dossier contenant une apostrophe ou du SQL ne peut rien casser).
    # RETURNING id demande à SQLite de renvoyer l'id qu'il vient d'attribuer.
    # fetchone() lit cette ligne de résultat.
    row = conn.execute(
        "INSERT INTO scans (root, scanned_at) VALUES (?, ?) RETURNING id",
        (str(root), datetime.now(UTC).isoformat()),
    ).fetchone()
    # commit valide l'écriture sur le disque. Sans commit, rien n'est enregistré.
    conn.commit()
    return int(row["id"])


# Insère tous les fichiers d'un scan et renvoie combien ont été insérés.
def insert_files(conn: sqlite3.Connection, scan_id: int, files: Iterable[FileInfo]) -> int:
    # Pour chaque FileInfo, on fabrique le tuple (scan_id, path, name, size, modified,
    # extension, mime, hash). astuple(file) donne les 7 champs dans l'ordre de la dataclass,
    # et l'étoile * les « déplie » dans le tuple, derrière scan_id.
    # C'est CETTE ligne qui parcourt le générateur scan() : c'est ici que le disque est lu,
    # fichier par fichier, au fur et à mesure que la liste se construit.
    rows = [(scan_id, *astuple(file)) for file in files]
    # executemany exécute le même INSERT pour chaque tuple de la liste, en une seule fois.
    # Les 8 ? correspondent aux 8 colonnes, dans le même ordre que le tuple.
    conn.executemany(
        "INSERT INTO files (scan_id, path, name, size, modified, extension, mime, hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


# Tous les scans, du plus récent au plus ancien. Utilisé par la commande « fsaudit scans ».
# fetchall() renvoie toutes les lignes sous forme de liste.
def list_scans(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()


# Le numéro du scan le plus récent, ou None si la base est vide. La CLI s'en sert quand
# on ne précise pas --scan ; si None, elle affiche « Aucun scan en base ».
# int | None dans la signature veut dire « renvoie un entier ou rien ».
def latest_scan_id(conn: sqlite3.Connection) -> int | None:
    # ORDER BY id DESC LIMIT 1 : trie du plus grand id au plus petit, garde le premier.
    # fetchone() renvoie cette ligne, ou None s'il n'y a aucune ligne.
    row = conn.execute("SELECT id FROM scans ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return int(row["id"])


# Toutes les lignes de fichiers d'un scan donné. Utilisé par le diff dans analysis.py,
# qui compare les fichiers de deux scans.
def files_of_scan(conn: sqlite3.Connection, scan_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM files WHERE scan_id = ?", (scan_id,)).fetchall()
