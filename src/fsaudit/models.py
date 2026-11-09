# dataclass est un décorateur : une fonction qui enrichit la classe écrite en dessous.
from dataclasses import dataclass


# Un FileInfo représente UN fichier trouvé pendant le scan. C'est exactement une ligne de la
# table "files" de la base SQLite.
#
# Sans @dataclass, il faudrait écrire à la main un __init__ qui reçoit 7 paramètres et les
# range dans self.path, self.name, etc. Le décorateur génère tout ça automatiquement à partir
# des annotations de type ci-dessous, ainsi que __repr__ (affichage lisible) et __eq__
# (comparaison de deux FileInfo champ par champ).
#
# frozen=True rend l'objet immuable : une fois créé, on ne peut plus changer ses champs.
# C'est logique, un fichier relevé ne change pas, et ça évite les modifications accidentelles.
#
# L'ORDRE des champs est important : il est identique à l'ordre des colonnes dans la requête
# INSERT INTO files de database.py. C'est ce qui permet d'utiliser astuple(file) là-bas
# pour transformer un FileInfo en tuple prêt à insérer, sans recopier les 7 champs.
@dataclass(frozen=True)
class FileInfo:
    path: str  # chemin relatif au dossier scanné, avec des "/", ex : "sub/b.txt"
    name: str  # nom du fichier seul, ex : "b.txt"
    size: int  # taille en octets
    modified: str  # date de dernière modification, en UTC, au format ISO 8601
    extension: str  # extension en minuscules, ex : ".txt" (vide si le fichier n'en a pas)
    mime: str  # type MIME deviné depuis l'extension, ex : "text/plain", sinon "unknown"
    hash: str  # empreinte SHA-256 du contenu, 64 caractères hexadécimaux


# Exemple d'utilisation : FileInfo(path="a.txt", name="a.txt", size=5, modified="2026-…",
# extension=".txt", mime="text/plain", hash="2cf24d…"). On lit ensuite info.size, info.hash…
