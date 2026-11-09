import logging
from pathlib import Path


def setup_logging(log_path: Path, level: str) -> None:
    # Sortie 1 : la console. On ne lui envoie que WARNING et plus grave,
    # pour ne pas mélanger les messages de routine avec les tableaux affichés.
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)

    # Sortie 2 : le fichier .log. Pas de filtre : il reçoit tout ce que le niveau global
    # laisse passer.
    log_file = logging.FileHandler(log_path, encoding="utf-8")

    # Configuration globale : niveau (INFO par défaut, depuis le .env), format d'une ligne,
    # et les deux sorties. force=True remplace une configuration déjà en place
    # (utile dans les tests qui lancent la CLI plusieurs fois).
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
        handlers=[console, log_file],
        force=True,
    )
