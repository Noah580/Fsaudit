# fsaudit

Outil en ligne de commande qui scanne un dossier, indexe ses fichiers dans SQLite, puis analyse le résultat : doublons, plus gros fichiers et répartition par extension, avec une extension de sauvegarde (`backup`).

## Lancer le projet

```bash
uv sync
uv run fsaudit --help
```

```bash
uv run fsaudit scan C:\Users\moi\Documents --exclude "*.jpg" --exclude ".git"
uv run fsaudit scans
uv run fsaudit dupes
uv run fsaudit top -n 10
uv run fsaudit ext
uv run fsaudit backup ~/Sauvegarde
```

Sur macOS / Linux, le dossier s'écrit par exemple `~/Documents` au lieu de `C:\Users\moi\Documents`.

Chaque commande d'analyse travaille par défaut sur le dernier scan, ou sur un scan précis avec `--scan 3`.

## Configuration (.env)

Le fichier `.env` (copier `.env.example`) est chargé par python-dotenv au démarrage :

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `FSAUDIT_DB` | fichier SQLite | `fsaudit.db` |
| `FSAUDIT_LOG` | fichier de log | `fsaudit.log` |
| `FSAUDIT_LOG_LEVEL` | niveau de log du fichier | `INFO` |
| `FSAUDIT_EXCLUDE` | motifs toujours exclus, séparés par des virgules | `.git,__pycache__,.venv` |

## Architecture

```
src/fsaudit/
  cli.py        les 7 commandes Typer + affichage des tableaux rich
  config.py     lecture du .env -> 4 constantes (DB_PATH, LOG_PATH, LOG_LEVEL, EXCLUDE)
  logs.py       logging vers la console (WARNING+) et le fichier .log (tout)
  models.py     dataclass FileInfo = une ligne de la table files
  scanner.py    parcours récursif, exclusions, hash SHA-256, type MIME
  database.py   schéma SQLite, insertion, liste des scans
  analysis.py   les analyses : doublons, top, répartition par extension
  backup.py     extension : copie des fichiers d'un scan vers un dossier de sauvegarde
tests/          un fichier de tests par couche (scanner, analyse, cli)
```

Un fichier = une responsabilité (principe SRP du cours). Le flux est toujours le même : `cli.py` lit les options, appelle `scanner`/`database`/`analysis`, puis affiche.

Base de données : une table `scans` (id, dossier, date) et une table `files` (une ligne par fichier, liée à un scan). Chaque scan garde ses propres fichiers, on peut donc analyser un ancien scan avec `--scan N`.

## Répartition des tâches (binôme)

| | Matthieu : indexation | Noah : analyses et CLI |
| --- | --- | --- |
| Code | `scanner.py`, `database.py`, `models.py`, `config.py`, `logs.py` | `analysis.py`, `cli.py`, `__main__.py`, `backup.py` |
| Tests | `tests/test_scanner.py` | `tests/test_analysis.py`, `tests/test_cli.py` |
| À expliquer | parcours `os.walk` et exclusions, hash SHA-256, type MIME, schéma SQLite et requêtes paramétrées, `.env`, logging console/fichier, gestion des erreurs sans arrêt du scan | requêtes doublons / top / extensions (`GROUP BY`), commandes Typer et options, tableaux rich, `CliRunner` dans les tests, extension `backup` |

En commun : `pyproject.toml`, ruff / mypy, README, dépôt GitHub.

Déroulé de la soutenance (15 min) :

1. Noah (2 min) : présentation de l'outil et démo live (`scan`, `dupes`, `top`, `ext`, `backup`).
2. Matthieu (4 min) : architecture, flux scan → SQLite, gestion des erreurs, configuration et logs.
3. Noah (4 min) : les analyses SQL, la couche CLI, l'extension backup.
4. Matthieu (2 min) : tests, ruff, mypy, limites et pistes d'extension.
5. Les deux (3 min) : questions.

## Choix techniques et justification

- **uv + structure `src/`** : demandé par le sujet. `uv run` crée et synchronise le venv tout seul, `uv.lock` garantit les mêmes versions chez les deux membres du binôme.
- **Typer** : chaque fonction décorée `@app.command()` devient une sous-commande, les types des paramètres donnent le parsing et le `--help` gratuitement. Moins de code qu'argparse.
- **rich** : installé avec Typer, sert uniquement à afficher des tableaux lisibles.
- **SQLite via `sqlite3`** : inclus dans Python, un simple fichier, pas de serveur. Toutes les requêtes sont paramétrées avec `?` (jamais de f-string) contre l'injection SQL.
- **`os.walk`** plutôt que `rglob` : on peut retirer des dossiers de `dirnames` pendant le parcours, donc un dossier exclu (`.git`) n'est même pas ouvert. `onerror` logge les dossiers illisibles sans arrêter le scan.
- **`fnmatch`** pour `--exclude` / `--include` : motifs shell (`*.jpg`) que tout le monde connaît, sans toucher au disque.
- **SHA-256 avec `hashlib.file_digest`** : le hash sert à détecter les doublons quel que soit le nom, et à savoir si un fichier est déjà à jour dans la sauvegarde. `file_digest` lit le fichier par blocs pour nous, donc pas de gros fichier chargé en mémoire. MD5 est évité car obsolète.
- **Chemins stockés relatifs au dossier scanné** : tableaux plus courts, et le backup reconstruit la même arborescence dans le dossier de sauvegarde.
- **Dates en UTC ISO 8601** : recommandation du cours, non ambigu.
- **Générateur `yield` dans `scan()`** : les fichiers sont produits un par un, le scan ne stocke jamais toute l'arborescence en mémoire.
- **Erreurs** : on tente l'opération et on attrape `OSError` (style EAFP). Le fichier fautif est loggé en WARNING et le scan continue. On n'attrape jamais `except:` générique.
- **Logging** : un logger par module (`logging.getLogger(__name__)`), la console ne montre que les problèmes (WARNING et plus), le fichier `.log` garde tout. Les valeurs sont passées en arguments `%s`, pas en f-string.
- **python-dotenv** : configuration sans toucher au code ; `.env` est dans le `.gitignore`, `.env.example` est versionné.
- **`@dataclass(frozen=True)`** pour `FileInfo` : juste un conteneur de données typé, immuable, avec `__init__` et `__repr__` générés.
- **Tests pytest** avec `tmp_path` (vrais fichiers temporaires), `monkeypatch` (simuler une `PermissionError`) et `CliRunner` de Typer (tester les commandes de bout en bout).
- **Qualité** : `ruff check` et `ruff format` pour PEP 8, `mypy --strict` pour le typage.

## Qualité

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## Extension réalisée : `fsaudit backup`

`fsaudit backup <dossier> [--scan N]` copie tous les fichiers d'un scan (par défaut le dernier) vers un dossier de sauvegarde, en gardant l'arborescence.

- **Sauvegarde incrémentale grâce au hash** : si le fichier existe déjà dans la sauvegarde avec le même SHA-256 que dans le scan, il n'est pas recopié. Relancer un backup ne copie donc que ce qui a changé. On réutilise le hash déjà calculé au scan au lieu d'en inventer un autre critère (date, taille) moins fiable.
- **`shutil.copy2`** : copie le contenu et conserve la date de modification du fichier.
- **Erreurs** : un fichier impossible à copier (supprimé depuis le scan, droits) est loggé en WARNING et le backup continue ; la commande liste ces fichiers et se termine avec le code 1.
- **Sécurité** : le dossier de sauvegarde ne peut pas être dans le dossier scanné, sinon chaque nouveau scan indexerait la sauvegarde elle-même.
- Logique dans `backup.py` (même découpage que `analysis.py`), la CLI ne fait qu'appeler et afficher. Testé dans `tests/test_cli.py`.

## Pistes d'extension

Export JSON/CSV d'une analyse, scan en threads pour les gros disques (I/O bound), barre de progression `tqdm`.

## Questions probables en soutenance

- *Pourquoi hasher tous les fichiers, c'est lent ?* C'est ce qui rend les doublons et le backup fiables indépendamment du nom et de la date. Une optimisation simple serait de ne hasher que les fichiers de même taille.
- *Que se passe-t-il si un fichier est illisible ?* `inspect_file` lève une `OSError`, le `except` dans `scan()` logge un WARNING avec le chemin et passe au suivant. Testé dans `test_scan_continues_after_error`.
- *Pourquoi des `?` dans les requêtes SQL ?* Requêtes paramétrées : le driver échappe les valeurs, aucune injection possible même avec un nom de fichier malveillant.
- *Pourquoi `os.walk` et pas `Path.rglob` ?* Pour élaguer les dossiers exclus avant d'y descendre via `dirnames[:] = ...`.
- *Pourquoi un `yield` ?* Le scanner est un générateur : mémoire constante, et `insert_files` consomme les fichiers au fil de l'eau.
- *À quoi sert `closing()` ?* `with closing(conn)` garantit la fermeture de la connexion SQLite même si une exception survient (context manager).
- *Pourquoi `--exclude` est répétable ?* Typer transforme un paramètre `list[str]` en option répétable : `-e "*.jpg" -e ".git"`.
