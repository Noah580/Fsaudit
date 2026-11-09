import sqlite3
from collections.abc import Iterable
from dataclasses import astuple
from datetime import UTC, datetime
from pathlib import Path

from fsaudit.models import FileInfo

# Deux tables :
# - scans : une ligne par lancement de "fsaudit scan" (historique). Plusieurs scans conservés
#   = possibilité de faire un diff entre deux d'entre eux.
# - files : une ligne par fichier trouvé, rattachée à son scan par scan_id.
# IF NOT EXISTS : ne plante pas si les tables existent déjà, on peut l'exécuter à chaque lancement.
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


def connect(db_path: Path) -> sqlite3.Connection:
    # Ouvre (ou crée) le fichier SQLite.
    conn = sqlite3.connect(db_path)
    # row_factory = Row permet d'écrire row["size"] au lieu de row[3].
    conn.row_factory = sqlite3.Row
    # Crée les tables si besoin.
    conn.executescript(SCHEMA)
    return conn


def create_scan(conn: sqlite3.Connection, root: Path) -> int:
    # Ajoute une ligne dans "scans" et récupère son id grâce à RETURNING.
    # Les ? sont remplacés par les valeurs du tuple : requête paramétrée, jamais de f-string,
    # c'est la protection de base contre l'injection SQL.
    row = conn.execute(
        "INSERT INTO scans (root, scanned_at) VALUES (?, ?) RETURNING id",
        (str(root), datetime.now(UTC).isoformat()),
    ).fetchone()
    conn.commit()
    return int(row["id"])


def insert_files(conn: sqlite3.Connection, scan_id: int, files: Iterable[FileInfo]) -> int:
    # astuple(file) transforme un FileInfo en tuple, dans l'ordre des champs,
    # qui est aussi l'ordre des colonnes ci-dessous. On ajoute scan_id devant.
    # C'est cette ligne qui parcourt réellement le générateur scan() : le disque est lu ici.
    rows = [(scan_id, *astuple(file)) for file in files]
    # executemany insère toutes les lignes d'un coup.
    conn.executemany(
        "INSERT INTO files (scan_id, path, name, size, modified, extension, mime, hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def list_scans(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    # Tous les scans, du plus récent au plus ancien.
    return conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()


def latest_scan_id(conn: sqlite3.Connection) -> int | None:
    # Le scan le plus récent, ou None si la base est vide
    # (la CLI affiche alors "Aucun scan en base").
    row = conn.execute("SELECT id FROM scans ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return int(row["id"])


def files_of_scan(conn: sqlite3.Connection, scan_id: int) -> list[sqlite3.Row]:
    # Toutes les lignes d'un scan, utilisé par le diff dans analysis.py.
    return conn.execute("SELECT * FROM files WHERE scan_id = ?", (scan_id,)).fetchall()
