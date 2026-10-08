# Tests

Run from the repository root with the existing virtual environment:

```sh
venv/bin/python -m pip install -r tests/requirements.txt
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -c tests/pytest.ini
```

Or run one module:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -c tests/pytest.ini tests/test_api.py -v
```

The suite uses pytest, pytest-asyncio, the application's dependencies, and httpx
for HTTP requests against the in-process FastAPI app. Tests use plain assertions,
pytest fixtures, and pytest.raises. The standard-library unittest.mock module
provides mocks only; there are no unittest test classes or runners.
No live database or U of T API is needed. Database operations and outbound HTTP
calls are mocked. Engine construction and dotenv loading are intercepted before
importing the app, so tests do not load local database credentials.

## Coverage map

| Source module | Tests |
| --- | --- |
| api.py | HTTP routes, filtering, validation, missing data, database dependency cleanup, lifespan |
| uoft_client.py | Request construction, response conversion, meetings, controls, sessions, transport failures |
| scrape.py | HTML/file/response parsing, optional fields, course extraction, command workflow |
| models.py | Course primary key and PostgreSQL DDL |
| schemas.py | Input constraints, nested response validation, ORM serialization, scalar/null shapes, OpenAPI contracts |
| create_engine.py | Environment configuration passed to the engine/session factories |
| init_database.py | URL parsing, connection fallback, SQL parameters, upsert rows, import workflow |

The empty package `__init__.py` is exercised by imports. Synthetic HTML lives in
`fixtures/`; nested API inputs are fresh dictionaries created by `support.py`.
Tests compare extracted codes as sets because their documented order is unspecified.

## Regression coverage

Regression tests verify that embedded course codes are rejected, empty offerings
are skipped or return HTTP 404, and unknown sections return HTTP 404.
Upstream HTTP failures, invalid JSON/data, connection errors, and timeouts are
tested separately. Route tests verify 502/504 responses without leaking upstream
error details. These regressions run as normal tests with no expected failures.

These are offline unit and HTTP tests, not PostgreSQL integration tests. They verify
SQL construction and supplied parameters but do not prove a real database accepts
the statements or that upstream response formats have remained unchanged.
