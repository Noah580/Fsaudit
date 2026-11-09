import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fsaudit import analysis, config, database, scanner
from fsaudit.backup import backup as run_backup
from fsaudit.logs import setup_logging

app = typer.Typer(help="Audit de fichiers : scan, doublons, top, répartition, backup.")
console = Console()


@app.callback()
def main() -> None:
    setup_logging(config.LOG_PATH, config.LOG_LEVEL)


def human_size(size: float) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"


def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def scan_root(conn: sqlite3.Connection, scan_id: int) -> Path:
    for row in database.list_scans(conn):
        if row["id"] == scan_id:
            return Path(row["root"])
    console.print(f"[red]Scan #{scan_id} introuvable : voir `fsaudit scans`.[/red]")
    raise typer.Exit(code=1)


def check_scan_exists(conn: sqlite3.Connection, scan_id: int) -> None:
    scan_root(conn, scan_id)


def pick_scan(conn: sqlite3.Connection, scan_id: int | None) -> int:
    if scan_id is not None:
        check_scan_exists(conn, scan_id)
        return scan_id
    latest = database.latest_scan_id(conn)
    if latest is None:
        console.print("[red]Aucun scan en base : lancez d'abord `fsaudit scan <dossier>`.[/red]")
        raise typer.Exit(code=1)
    return latest


ScanOption = Annotated[
    int | None, typer.Option("--scan", "-s", help="Id du scan (défaut : dernier)")
]


@app.command()
def scan(
    root: Annotated[Path, typer.Argument(exists=True, file_okay=False, help="Dossier à indexer")],
    exclude: Annotated[
        list[str] | None, typer.Option("--exclude", "-e", help="Motif à exclure")
    ] = None,
    include: Annotated[
        list[str] | None, typer.Option("--include", "-i", help="Motif à inclure")
    ] = None,
) -> None:
    """Parcourt un dossier et indexe ses fichiers dans SQLite."""
    with closing(database.connect(config.DB_PATH)) as conn:
        scan_id = database.create_scan(conn, root)
        files = scanner.scan(root, config.EXCLUDE + (exclude or []), include or [])
        count = database.insert_files(conn, scan_id, files)
    console.print(f"Scan #{scan_id} : {count} fichiers indexés depuis {root}")


@app.command()
def scans() -> None:
    """Liste les scans enregistrés."""
    with closing(database.connect(config.DB_PATH)) as conn:
        rows = database.list_scans(conn)
    print_table(
        "Scans",
        ["Id", "Dossier", "Date (UTC)"],
        [[str(r["id"]), r["root"], r["scanned_at"][:19]] for r in rows],
    )


@app.command()
def dupes(scan_id: ScanOption = None) -> None:
    """Détecte les doublons et l'espace récupérable."""
    with closing(database.connect(config.DB_PATH)) as conn:
        chosen = pick_scan(conn, scan_id)
        rows = analysis.duplicates(conn, chosen)
    table_rows = []
    recoverable = 0
    for r in rows:
        saved = r["size"] * (r["copies"] - 1)
        recoverable += saved
        table_rows.append(
            [r["hash"][:12], str(r["copies"]), human_size(r["size"]), human_size(saved), r["paths"]]
        )
    print_table(
        f"Doublons du scan #{chosen}",
        ["Hash", "Copies", "Taille", "Récupérable", "Fichiers"],
        table_rows,
    )
    console.print(f"Espace récupérable total : {human_size(recoverable)}")


@app.command()
def top(
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Nombre de fichiers")] = 10,
    scan_id: ScanOption = None,
) -> None:
    """Affiche les fichiers les plus volumineux."""
    with closing(database.connect(config.DB_PATH)) as conn:
        chosen = pick_scan(conn, scan_id)
        rows = analysis.biggest(conn, chosen, limit)
    print_table(
        f"Top {limit} du scan #{chosen}",
        ["Fichier", "Taille", "MIME"],
        [[r["path"], human_size(r["size"]), r["mime"]] for r in rows],
    )


@app.command()
def ext(scan_id: ScanOption = None) -> None:
    """Répartition de l'espace par extension."""
    with closing(database.connect(config.DB_PATH)) as conn:
        chosen = pick_scan(conn, scan_id)
        rows = analysis.by_extension(conn, chosen)
    print_table(
        f"Répartition par extension du scan #{chosen}",
        ["Extension", "Fichiers", "Taille totale"],
        [[r["extension"] or "(aucune)", str(r["count"]), human_size(r["total"])] for r in rows],
    )


@app.command()
def backup(
    dest: Annotated[Path, typer.Argument(file_okay=False, help="Dossier de sauvegarde")],
    scan_id: ScanOption = None,
) -> None:
    """Copie les fichiers d'un scan vers un dossier, sans recopier ceux déjà à jour."""
    with closing(database.connect(config.DB_PATH)) as conn:
        chosen = pick_scan(conn, scan_id)
        source = scan_root(conn, chosen)
        if dest.resolve().is_relative_to(source.resolve()):
            console.print(
                "[red]Le dossier de sauvegarde ne doit pas être dans le dossier scanné.[/red]"
            )
            raise typer.Exit(code=1)
        result = run_backup(conn, chosen, source, dest)
    console.print(
        f"Backup du scan #{chosen} vers {dest} : {len(result.copied)} copiés, "
        f"{len(result.skipped)} déjà à jour, {len(result.failed)} en erreur"
    )
    if result.failed:
        print_table("Fichiers non copiés", ["Fichier"], [[path] for path in result.failed])
        raise typer.Exit(code=1)
