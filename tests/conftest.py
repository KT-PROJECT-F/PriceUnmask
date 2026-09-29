"""Shared test fixtures: an isolated in-memory database per test."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from backend.db import models  # noqa: F401  (register models)
from backend.db.database import Base, make_engine


@pytest.fixture
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        yield s
