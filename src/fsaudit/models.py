from dataclasses import dataclass


# Un FileInfo = un fichier trouvé pendant le scan = une ligne de la table "files".
# @dataclass génère automatiquement __init__, __repr__ et __eq__.
# frozen=True rend l'objet immuable : on ne modifie pas un fichier déjà relevé.
# L'ORDRE des champs est important : il correspond à l'ordre des colonnes
# dans l'INSERT de database.py (grâce à astuple).
@dataclass(frozen=True)
class FileInfo:
    path: str  # chemin relatif au dossier scanné, ex : "sub/b.txt"
    name: str  # nom du fichier seul, ex : "b.txt"
    size: int  # taille en octets
    modified: str  # date de modification en UTC, format ISO 8601
    extension: str  # ex : ".txt" (en minuscules)
    mime: str  # ex : "text/plain", ou "unknown"
    hash: str  # empreinte SHA-256 du contenu, en hexadécimal
