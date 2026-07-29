"""Shared pytest fixtures for API integration tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app import models  # noqa: F401 — registers models in Base.metadata


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """Create the schema in the test database once per test session."""
    engine = create_engine(settings.test_database_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Provide a session whose writes are rolled back after each test.

    The session joins an outer transaction using a savepoint, so commits issued
    by the application are undone when the outer transaction is rolled back.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """Provide a test client wired to the rolled-back database session."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()