"""Shared HTTP test fixtures."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app
from tests.support.in_memory_store import InMemorySession


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    session = InMemorySession()
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
