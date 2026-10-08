"""Function-scoped fixtures for isolated API tests."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
import psycopg
import requests

from tests.support import api, models, response


@pytest.fixture(autouse=True)
def block_live_services(monkeypatch):
    """Require explicit mocks for outbound HTTP and PostgreSQL connections."""
    def blocked(*args, **kwargs):
        raise AssertionError("Live service access is disabled in tests; mock this call.")

    monkeypatch.setattr(psycopg, "connect", blocked)
    monkeypatch.setattr(requests.sessions.Session, "request", blocked)


@pytest.fixture
def course():
    return models.Course(
        course_code="CSC108H1", title="Programming", prerequisites="MAT135H1",
        prerequisite_course_list=["MAT135H1"], recommended="Practice",
        exclusion="CSC120H1",
    )


@pytest.fixture
def db(course):
    session = MagicMock()
    session.get = AsyncMock(return_value=course)
    session.scalars = AsyncMock(return_value=MagicMock())
    session.close = AsyncMock()
    return session


@pytest.fixture
def upstream(monkeypatch):
    fetch = MagicMock(return_value=response())
    monkeypatch.setattr(api, "call_uoft_api", fetch)
    return fetch


@pytest_asyncio.fixture
async def http(db, upstream, monkeypatch):
    @asynccontextmanager
    async def session():
        try:
            yield db
        finally:
            await db.close()

    monkeypatch.setattr(api, "AsyncSessionLocal", session)
    previous = api.app.dependency_overrides.copy()
    api.app.dependency_overrides[api.get_db] = lambda: db
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://test"
        ) as client:
            yield client
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previous)
