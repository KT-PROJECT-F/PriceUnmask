"""Database engine and session setup (SQLAlchemy 2.0).

Owner: DB track. Everyone else only uses `get_session` (FastAPI) or `SessionLocal` (scripts).
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """Parent class for every ORM model."""


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        # Make sure the folder for the .db file exists.
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        url,
        # The scheduler thread and API threads share one SQLite file.
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")  # SQLite ignores FKs unless told
            cur.execute("PRAGMA journal_mode=WAL")  # readers do not block the scraper's writes
            cur.close()

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(bind: Engine | None = None) -> None:
    """Create all tables. Safe to call repeatedly."""
    from backend.db import models  # noqa: F401  (registers models on Base)

    Base.metadata.create_all(bind or engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
