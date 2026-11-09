# pytest découvre automatiquement les fichiers test_*.py et les fonctions test_*.
# Un test est une simple fonction avec des assert : si un assert est faux, le test échoue.
import logging
from pathlib import Path

import pytest

from fsaudit import scanner


# Fonction d'aide (pas un test, son nom ne commence pas par test_) : crée une mini
# arborescence dans le dossier reçu : 2 fichiers texte, une image, un dossier .git.
def make_tree(root: Path) -> None:
    (root / "a.txt").write_text("hello")
    (root / "sub").mkdir()
    (root / "sub" / "b.txt").write_text("world")
    (root / "photo.jpg").write_bytes(b"\xff\xd8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("secret")


# tmp_path est une « fixture » fournie par pytest : quand une fonction de test a un paramètre
# nommé tmp_path, pytest lui passe un dossier temporaire neuf, supprimé après le test.
# Chaque test travaille donc sur de vrais fichiers, sans toucher au disque de l'utilisateur.


# L'empreinte SHA-256 du texte "hello" est une valeur connue et fixe dans le monde entier.
# Si hash_file la renvoie, c'est qu'elle calcule bien du SHA-256.
def test_hash_file(tmp_path: Path) -> None:
    file = tmp_path / "a.txt"
    file.write_text("hello")
    expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert scanner.hash_file(file) == expected


# Sans aucun motif, tout est indexé, y compris .git/config. On vérifie aussi que les chemins
# sont relatifs ("sub/b.txt" et pas C:\...\sub\b.txt).
# {file.path for file in ...} est une compréhension d'ensemble : on récupère juste les chemins.
def test_scan_indexes_all_files(tmp_path: Path) -> None:
    make_tree(tmp_path)
    paths = {file.path for file in scanner.scan(tmp_path, [], [])}
    assert paths == {"a.txt", "sub/b.txt", "photo.jpg", ".git/config"}


# ".git" exclut le dossier entier (donc .git/config disparaît), "*.jpg" exclut la photo.
def test_scan_exclude_patterns(tmp_path: Path) -> None:
    make_tree(tmp_path)
    paths = {file.path for file in scanner.scan(tmp_path, [".git", "*.jpg"], [])}
    assert paths == {"a.txt", "sub/b.txt"}


# Avec --include "*.jpg", seule la photo est gardée.
def test_scan_include_patterns(tmp_path: Path) -> None:
    make_tree(tmp_path)
    paths = {file.path for file in scanner.scan(tmp_path, [], ["*.jpg"])}
    assert paths == {"photo.jpg"}


# Vérifie les champs relevés par inspect_file sur a.txt ("hello" = 5 octets).
def test_file_info_fields(tmp_path: Path) -> None:
    make_tree(tmp_path)
    info = scanner.inspect_file(tmp_path / "a.txt", tmp_path)
    assert info.name == "a.txt"
    assert info.size == 5
    assert info.extension == ".txt"
    assert info.mime == "text/plain"


# LE test important : le scan doit continuer quand un fichier est illisible.
# On ne peut pas facilement créer un vrai fichier protégé sur Windows, alors on simule.
# monkeypatch et caplog sont deux autres fixtures pytest.
def test_scan_continues_after_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    make_tree(tmp_path)

    # Fausse fonction de hash : elle lève PermissionError pour a.txt, comme si le système
    # refusait l'accès, et renvoie "ok" pour les autres fichiers.
    # PermissionError est une sous-classe d'OSError, donc le except OSError de scan() l'attrape.
    def failing_hash(path: Path) -> str:
        if path.name == "a.txt":
            raise PermissionError(13, "Permission denied", str(path))
        return "ok"

    # monkeypatch.setattr remplace scanner.hash_file par notre fausse fonction, le temps de
    # ce test seulement. pytest remet la vraie fonction à la fin automatiquement.
    monkeypatch.setattr(scanner, "hash_file", failing_hash)
    # caplog capture tous les logs de niveau WARNING ou plus émis dans le bloc with.
    with caplog.at_level(logging.WARNING):
        paths = {file.path for file in scanner.scan(tmp_path, [".git", "*.jpg"], [])}
    # a.txt a échoué, mais b.txt est bien indexé : le scan a continué.
    assert paths == {"sub/b.txt"}
    # Et l'erreur a été loggée avec notre message.
    assert "Fichier ignoré" in caplog.text
