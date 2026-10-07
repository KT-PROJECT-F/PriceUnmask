"""Export a consistent copy of the live SQLite database.

Exporting the database
----------------------
Run:

    python -m backend.devtools.export_db

The exported database is written to:

    data/exports/priceunmask-<UTC timestamp>.db

Exported *.db files must never be committed to Git.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def sqlite_url_to_path(database_url: str) -> Path:
    """Convert a SQLite database URL into a filesystem path."""
    if not database_url.startswith("sqlite:///"):
        raise ValueError(f"Unsupported database URL: {database_url}")

    parsed = urlparse(database_url)

    if parsed.scheme != "sqlite":
        raise ValueError(f"Unsupported database URL: {database_url}")

    path = unquote(parsed.path)

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

    if source_path.suffix.lower() != ".db":
        raise ValueError(f"Database export requires a SQLite .db file: {source_path}")

    if not source_path.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source_path}")

    destination_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination_path = destination_folder / f"priceunmask-{timestamp}.db"

    with (
        sqlite3.connect(source_path) as source,
        sqlite3.connect(destination_path) as destination,
    ):
        source.backup(destination)

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
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"Database export failed: {exc}") from exc

    print(f"Database exported to: {destination}")


if __name__ == "__main__":
    main()
