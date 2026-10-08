"""Export a consistent copy of the live SQLite database.

Exporting the database
----------------------
Run:

    python -m backend.devtools.export_db

The exported database is written to:

    data/exports/priceunmask-<UTC timestamp>.db

Exported *.db files must never be committed to Git.

Using an exported copy
----------------------
Copy the file to ``data/priceunmask.db`` (or point ``DATABASE_URL`` at it, for example
``DATABASE_URL=sqlite:///data/exports/priceunmask-<timestamp>.db``) and start the app.
The copy is a normal SQLite file; it does not need the ``-wal`` or ``-shm`` files.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def sqlite_url_to_path(database_url: str) -> Path:
    """Convert a SQLite database URL into a filesystem path."""
    if not database_url.startswith("sqlite:///"):
        raise ValueError(f"Unsupported database URL: {database_url}")

    path = unquote(urlparse(database_url).path)

    if not path:
        raise ValueError(f"SQLite database path is empty: {database_url}")

    # sqlite:///relative/path.db -> relative/path.db
    # sqlite:////absolute/path.db -> /absolute/path.db
    if database_url.startswith("sqlite:////"):
        return Path(path)

    return Path(path.lstrip("/"))


def export_db(source_path: Path, destination_folder: Path) -> Path:
    """Create a consistent SQLite backup and return its destination path."""
    source_path = Path(source_path)
    destination_folder = Path(destination_folder)

    if source_path.suffix.lower() not in SQLITE_SUFFIXES:
        raise ValueError(
            f"Database export requires a SQLite file (.db, .sqlite, .sqlite3): {source_path}"
        )

    if not source_path.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source_path}")

    destination_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination_path = destination_folder / f"priceunmask-{timestamp}.db"

    if destination_path.exists():
        raise FileExistsError(f"Export already exists, try again in a second: {destination_path}")

    try:
        # "with sqlite3.connect(...)" only commits; closing() really closes
        # the connection.
        with (
            closing(sqlite3.connect(source_path)) as source,
            closing(sqlite3.connect(destination_path)) as destination,
        ):
            source.backup(destination)
    except sqlite3.Error:
        destination_path.unlink(missing_ok=True)
        raise

    return destination_path


def main() -> None:
    """Export the configured live database."""
    from backend.config import settings

    try:
        source_path = sqlite_url_to_path(settings.database_url)
        destination = export_db(
            source_path=source_path,
            destination_folder=Path("data/exports"),
        )
    except (ValueError, OSError, sqlite3.Error) as exc:
        raise SystemExit(f"Database export failed: {exc}") from exc

    print(f"Database exported to: {destination}")


if __name__ == "__main__":
    main()
