import logging
from pathlib import Path

import pytest

from fsaudit import scanner


def make_tree(root: Path) -> None:
    # Mini arborescence de test : 2 fichiers texte, une image, un dossier .git.
    (root / "a.txt").write_text("hello")
    (root / "sub").mkdir()
    (root / "sub" / "b.txt").write_text("world")
    (root / "photo.jpg").write_bytes(b"\xff\xd8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("secret")


# tmp_path est une fixture pytest : un dossier temporaire neuf pour chaque test.


def test_hash_file(tmp_path: Path) -> None:
    # L'empreinte SHA-256 de "hello" est une valeur connue et fixe.
    file = tmp_path / "a.txt"
    file.write_text("hello")
    expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert scanner.hash_file(file) == expected


def test_scan_indexes_all_files(tmp_path: Path) -> None:
    # Sans aucun motif, tout est indexé, avec des chemins relatifs.
    make_tree(tmp_path)
    paths = {file.path for file in scanner.scan(tmp_path, [], [])}
    assert paths == {"a.txt", "sub/b.txt", "photo.jpg", ".git/config"}


def test_scan_exclude_patterns(tmp_path: Path) -> None:
    # ".git" exclut le dossier entier, "*.jpg" exclut le fichier.
    make_tree(tmp_path)
    paths = {file.path for file in scanner.scan(tmp_path, [".git", "*.jpg"], [])}
    assert paths == {"a.txt", "sub/b.txt"}


def test_scan_include_patterns(tmp_path: Path) -> None:
    # Avec --include, seuls les fichiers correspondants sont gardés.
    make_tree(tmp_path)
    paths = {file.path for file in scanner.scan(tmp_path, [], ["*.jpg"])}
    assert paths == {"photo.jpg"}


def test_file_info_fields(tmp_path: Path) -> None:
    make_tree(tmp_path)
    info = scanner.inspect_file(tmp_path / "a.txt", tmp_path)
    assert info.name == "a.txt"
    assert info.size == 5
    assert info.extension == ".txt"
    assert info.mime == "text/plain"


def test_scan_continues_after_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    make_tree(tmp_path)

    # Fausse fonction de hash : échoue sur a.txt, comme si le fichier était protégé.
    def failing_hash(path: Path) -> str:
        if path.name == "a.txt":
            raise PermissionError(13, "Permission denied", str(path))
        return "ok"

    # monkeypatch remplace scanner.hash_file par la fausse, le temps de ce test seulement.
    monkeypatch.setattr(scanner, "hash_file", failing_hash)
    # caplog capture les logs émis pendant le bloc.
    with caplog.at_level(logging.WARNING):
        paths = {file.path for file in scanner.scan(tmp_path, [".git", "*.jpg"], [])}
    # Le scan a continué : b.txt est bien indexé, et l'erreur a été loggée.
    assert paths == {"sub/b.txt"}
    assert "Fichier ignoré" in caplog.text
