# hashlib : calcul d'empreintes (SHA-256). logging : journalisation. mimetypes : deviner le
# type MIME d'un fichier depuis son extension. os : pour os.walk, le parcours récursif.
import hashlib
import logging
import mimetypes
import os

# Iterator sert uniquement au typage : scan() renvoie "quelque chose qu'on parcourt avec for".
from collections.abc import Iterator

# UTC est le fuseau horaire de référence, datetime manipule les dates.
from datetime import UTC, datetime

# fnmatch compare un nom de fichier à un motif shell comme "*.jpg".
from fnmatch import fnmatch
from pathlib import Path

# Notre propre dataclass, définie dans models.py.
from fsaudit.models import FileInfo

# Un logger par module, comme recommandé en cours. __name__ vaut "fsaudit.scanner" :
# c'est ce nom qui apparaît dans chaque ligne du fichier de log.
logger = logging.getLogger(__name__)


# Renvoie True si le nom correspond à AU MOINS un des motifs.
# fnmatch("photo.jpg", "*.jpg") -> True ; fnmatch("photo.jpg", ".git") -> False.
# any() parcourt les motifs et s'arrête au premier qui correspond. Avec une liste vide,
# any() renvoie False : sans motif d'exclusion, rien n'est exclu.
def matches(name: str, patterns: list[str]) -> bool:
    return any(fnmatch(name, pattern) for pattern in patterns)


# Calcule l'empreinte SHA-256 du contenu d'un fichier.
# "rb" = lecture en binaire, car on hashe des octets, pas du texte.
# with garantit que le fichier est refermé à la fin du bloc, même en cas d'erreur.
# file_digest lit le fichier par petits blocs : un fichier de plusieurs Go n'est jamais chargé
# entier en mémoire. hexdigest() renvoie l'empreinte en texte (64 caractères).
# Deux fichiers au contenu identique ont la même empreinte : c'est ainsi que l'analyse trouve
# les doublons et les fichiers déplacés, quel que soit leur nom.
def hash_file(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


# Fabrique le FileInfo d'un fichier. root est le dossier scanné, utile pour le chemin relatif.
def inspect_file(path: Path, root: Path) -> FileInfo:
    # stat() interroge le système une seule fois et renvoie taille, dates, permissions…
    stat = path.stat()
    # guess_type renvoie un couple (type, encodage), ex ("image/jpeg", None).
    # On ne garde que le type ; "_" est la convention pour « valeur qu'on ignore ».
    mime, _ = mimetypes.guess_type(path.name)
    return FileInfo(
        # relative_to(root) enlève le début du chemin : C:\dossier\sub\b.txt -> sub\b.txt.
        # as_posix() remplace les "\" par des "/" pour avoir la même écriture sur tous les OS.
        path=path.relative_to(root).as_posix(),
        name=path.name,
        size=stat.st_size,
        # st_mtime est un nombre de secondes depuis 1970. fromtimestamp le convertit en date,
        # tz=UTC lui donne un fuseau (date « aware », recommandée en cours),
        # isoformat() donne un texte du type 2026-11-09T10:18:02+00:00.
        modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        # suffix = l'extension avec le point (".txt"). lower() pour que ".JPG" et ".jpg"
        # soient comptés ensemble dans la répartition par extension.
        extension=path.suffix.lower(),
        # Si guess_type ne sait pas (None), on écrit "unknown" plutôt que de laisser vide.
        mime=mime or "unknown",
        hash=hash_file(path),
    )


# Appelée automatiquement par os.walk quand un DOSSIER ne peut pas être ouvert
# (ex : « Ma musique : Accès refusé »). On logge en WARNING et os.walk continue ailleurs.
def log_walk_error(error: OSError) -> None:
    logger.warning("Dossier inaccessible %s : %s", error.filename, error.strerror)


# La fonction principale : parcourt root récursivement et produit un FileInfo par fichier.
# exclude : motifs à ignorer (dossiers ET fichiers). include : si non vide, ne garder que
# les fichiers qui correspondent.
#
# Comme elle contient yield, cette fonction est un GÉNÉRATEUR : l'appeler ne parcourt rien.
# Elle renvoie un objet qu'on parcourt avec for ; à chaque fichier demandé, elle avance jusqu'au
# prochain yield puis se met en pause. Un seul FileInfo existe en mémoire à la fois, même pour
# un disque d'un million de fichiers. Celui qui la parcourt, c'est insert_files() dans
# database.py : c'est donc là-bas que le disque est réellement lu.
def scan(root: Path, exclude: list[str], include: list[str]) -> Iterator[FileInfo]:
    # Niveau INFO : visible dans le fichier .log, pas à l'écran.
    # On passe root en argument (%s) et pas dans une f-string : le message n'est construit
    # que s'il doit être émis, recommandation du cours.
    logger.info("Début du scan de %s", root)

    # os.walk descend dans tous les sous-dossiers. À chaque dossier rencontré, il donne :
    # dirpath = son chemin, dirnames = la liste de ses sous-dossiers, filenames = ses fichiers.
    # Il descend ensuite dans les dossiers listés dans dirnames.
    for dirpath, dirnames, filenames in os.walk(root, onerror=log_walk_error):
        # On retire les dossiers exclus de dirnames AVANT qu'os.walk n'y descende :
        # un dossier .git n'est donc jamais ouvert. C'est la raison du choix d'os.walk
        # plutôt que Path.rglob, qui ne permet pas cet élagage.
        # dirnames[:] = ... remplace le CONTENU de la liste existante, celle qu'os.walk utilise.
        # dirnames = ... créerait une nouvelle liste qu'os.walk ne verrait pas.
        dirnames[:] = [name for name in dirnames if not matches(name, exclude)]

        for filename in filenames:
            # Fichier dont le nom correspond à un motif exclu : on passe au suivant.
            if matches(filename, exclude):
                continue
            # Si des motifs --include ont été donnés, on ignore les fichiers qui n'y
            # correspondent pas. Sans --include (liste vide), on garde tout.
            if include and not matches(filename, include):
                continue

            # L'opérateur / de pathlib assemble deux morceaux de chemin, avec le bon séparateur
            # selon l'OS. Équivalent de os.path.join.
            path = Path(dirpath) / filename

            # Style EAFP (vu en cours) : on tente, et on gère l'erreur si elle arrive.
            # OSError regroupe toutes les erreurs système sur un fichier : permission refusée,
            # fichier verrouillé par un autre programme, fichier supprimé entre temps…
            # Dans ce cas on logge un WARNING avec le chemin et le message système,
            # et la boucle passe au fichier suivant : le scan ne s'arrête JAMAIS.
            # On n'attrape que OSError, jamais "except:" nu qui masquerait nos propres bugs.
            try:
                yield inspect_file(path, root)
            except OSError as error:
                logger.warning("Fichier ignoré %s : %s", path, error.strerror)

    logger.info("Fin du scan de %s", root)
