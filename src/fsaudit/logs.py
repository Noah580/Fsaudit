# Le module logging est le système de journalisation de Python. Contrairement à print(),
# il horodate les messages, les classe par niveau (DEBUG < INFO < WARNING < ERROR < CRITICAL)
# et peut les envoyer vers plusieurs sorties à la fois : ici la console ET un fichier.
import logging
from pathlib import Path


# Cette fonction est appelée une seule fois, au démarrage de la CLI (dans cli.py, fonction main),
# avec les valeurs LOG_PATH et LOG_LEVEL lues dans config.py.
def setup_logging(log_path: Path, level: str) -> None:
    # Un "handler" est une sortie. StreamHandler envoie vers la console (la sortie d'erreur).
    console = logging.StreamHandler()
    # On règle cette sortie sur WARNING : elle n'affichera que WARNING, ERROR et CRITICAL.
    # Les messages INFO (comme « Début du scan ») n'iront donc pas à l'écran, pour ne pas
    # polluer les tableaux que la CLI affiche.
    console.setLevel(logging.WARNING)

    # Deuxième sortie : le fichier fsaudit.log. Pas de setLevel ici, donc il reçoit tout ce que
    # le niveau global laisse passer (INFO et plus par défaut). encoding="utf-8" pour que
    # les accents soient écrits correctement.
    log_file = logging.FileHandler(log_path, encoding="utf-8")

    # basicConfig fait la configuration globale en une fois :
    # - level : le niveau minimum pris en compte, ex "INFO" (les DEBUG sont ignorés)
    # - format : à quoi ressemble une ligne, ex « 2026-11-09 10:18:02 WARNING fsaudit.scanner : … »
    #   %(asctime)s = la date, %(levelname)s = le niveau, %(name)s = le module émetteur,
    #   %(message)s = le texte
    # - handlers : nos deux sorties
    # - force=True : si une configuration existait déjà, on la remplace. Utile dans les tests
    #   qui lancent la CLI plusieurs fois dans le même processus Python.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s : %(message)s",
        handlers=[console, log_file],
        force=True,
    )


# Résultat : un logger.info(...) va dans le fichier seulement ; un logger.warning(...) va dans
# le fichier ET à l'écran. C'est ce qu'on a vu avec « Dossier inaccessible … Accès refusé ».
