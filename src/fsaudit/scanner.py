import hashlib
import logging
import mimetypes
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

from fsaudit.models import FileInfo

# Un logger par module : son nom sera "fsaudit.scanner" dans le fichier de log.
logger = logging.getLogger(__name__)


def matches(name: str, patterns: list[str]) -> bool:
    # Vrai si le nom correspond à AU MOINS un motif shell (ex : "*.jpg", ".git").
    # any() s'arrête au premier motif qui correspond. Liste vide -> False.
    return any(fnmatch(name, pattern) for pattern in patterns)


def hash_file(path: Path) -> str:
    # Ouverture en binaire ("rb") car on hashe des octets, pas du texte.
    # file_digest lit le fichier par blocs : un gros fichier n'est jamais chargé entier en mémoire.
    # Deux fichiers au contenu identique ont la même empreinte : c'est ainsi qu'on trouve
    # les doublons.
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def inspect_file(path: Path, root: Path) -> FileInfo:
    # Un seul appel système pour récupérer taille et date de modification.
    stat = path.stat()
    # guess_type devine le MIME à partir de l'extension : ("image/jpeg", None).
    # On ignore le 2e élément.
    mime, _ = mimetypes.guess_type(path.name)
    return FileInfo(
        # Chemin relatif au dossier scanné, avec des "/" : C:\dossier\sub\b.txt -> "sub/b.txt"
        path=path.relative_to(root).as_posix(),
        name=path.name,
        size=stat.st_size,
        # st_mtime = secondes depuis 1970 -> date avec fuseau UTC -> texte ISO 8601
        modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        # .lower() pour que ".JPG" et ".jpg" comptent pareil dans la répartition par extension
        extension=path.suffix.lower(),
        mime=mime or "unknown",
        hash=hash_file(path),
    )


def log_walk_error(error: OSError) -> None:
    # Appelée par os.walk quand un DOSSIER ne peut pas être lu (ex : "Accès refusé").
    logger.warning("Dossier inaccessible %s : %s", error.filename, error.strerror)


def scan(root: Path, exclude: list[str], include: list[str]) -> Iterator[FileInfo]:
    # Grâce à yield, cette fonction est un générateur : les fichiers sortent un par un,
    # à la demande, sans jamais stocker toute l'arborescence en mémoire.
    logger.info("Début du scan de %s", root)

    # os.walk parcourt récursivement : pour chaque dossier, il donne son chemin,
    # la liste de ses sous-dossiers et la liste de ses fichiers.
    for dirpath, dirnames, filenames in os.walk(root, onerror=log_walk_error):
        # On retire les dossiers exclus de la liste AVANT qu'os.walk n'y descende.
        # dirnames[:] = ... modifie la liste en place (celle qu'os.walk utilise) ;
        # dirnames = ... créerait une nouvelle liste qu'os.walk ignorerait.
        dirnames[:] = [name for name in dirnames if not matches(name, exclude)]

        for filename in filenames:
            # Fichier exclu -> on passe au suivant.
            if matches(filename, exclude):
                continue
            # Si des motifs --include sont donnés, on ne garde que les fichiers qui y correspondent.
            if include and not matches(filename, include):
                continue

            # L'opérateur / assemble deux chemins (équivalent de os.path.join).
            path = Path(dirpath) / filename

            # Style EAFP : on tente, et si le système refuse (permission, fichier verrouillé,
            # fichier supprimé entre temps...), on logge un WARNING et le scan CONTINUE.
            try:
                yield inspect_file(path, root)
            except OSError as error:
                logger.warning("Fichier ignoré %s : %s", path, error.strerror)

    logger.info("Fin du scan de %s", root)
