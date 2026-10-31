"""Fixtures: a test database, catalogues in it, and web apps with clients signed in as different
players.

The tests that need a database use WARAGENTS_TEST_DATABASE_URL (from the environment or
python/.env). It must be a database of its own, because the tests wipe it. Without it those tests
are skipped and the engine tests still run.
"""

import os

import pytest

from waragents.catalogue import Catalogue
from waragents.content import seed
from waragents.db import URL_VARIABLE, Database, load_env
from waragents.db.migrate import migrate
from waragents.web.app import create_app

BUNDLED = {"maps": ["basic", "islands", "skirmish"], "trees": ["defend", "graze", "guard", "raid", "wander"]}
PASSWORD = "correct horse"


@pytest.fixture(scope="session")
def database():
    """The test database, emptied and migrated once per run."""
    load_env()
    url = os.environ.get("WARAGENTS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set WARAGENTS_TEST_DATABASE_URL to run the tests that need a database")
    if url == os.environ.get(URL_VARIABLE):
        pytest.exit("WARAGENTS_TEST_DATABASE_URL is the game's own database, which the tests would wipe")
    db = Database(url, max_size=4)
    db.execute("drop schema public cascade; create schema public")
    migrate(db)
    yield db
    db.close()


@pytest.fixture
def empty_catalogue(database):
    """A catalogue with nothing in it."""
    tables = [r["tablename"] for r in database.query(
        "select tablename from pg_tables where schemaname = 'public' and tablename <> 'schema_migrations'")]
    database.execute(f"truncate {', '.join(tables)} cascade")
    return Catalogue(database)


@pytest.fixture
def catalogue(empty_catalogue):
    """A catalogue with the bundled maps and trees, but no tutorials."""
    seed(empty_catalogue, only=BUNDLED)
    return empty_catalogue


@pytest.fixture
def app(catalogue):
    return create_app(catalogue)


def sign_up(app, name, password=PASSWORD):
    """A client for a new account, signed in."""
    client = app.test_client()
    response = client.post("/api/auth/register", json={"name": name, "password": password})
    assert response.status_code == 201, response.json
    return client


def sign_in(app, name, password=PASSWORD):
    client = app.test_client()
    response = client.post("/api/auth/login", json={"name": name, "password": password})
    assert response.status_code == 200, response.json
    return client


@pytest.fixture
def client(app):
    """Signed in as the first account on the server, which makes it an admin."""
    return sign_up(app, "Admin")
