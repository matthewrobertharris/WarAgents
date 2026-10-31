"""Fixtures: a database schema of the tests' own, catalogues in it, and web apps with clients
signed in as different players.

The tests that need a database use the game's database (WARAGENTS_DATABASE_URL, from the
environment or python/.env), but make a schema of their own in it for each run and drop it at the
end, so the game's data is never touched. Without a database those tests are skipped and the
engine tests still run.
"""

import os
import secrets

import psycopg
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
    """The game's database, with the tests' own freshly migrated schema."""
    load_env()
    url = os.environ.get(URL_VARIABLE)
    if not url:
        pytest.skip(f"Set {URL_VARIABLE} to run the tests that need a database")
    schema = f"pytest_{os.getpid()}_{secrets.token_hex(3)}"
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(f"create schema {schema}")
    db = Database(url, max_size=4, schema=schema)
    try:
        migrate(db)
        yield db
    finally:
        db.close()
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(f"drop schema {schema} cascade")


@pytest.fixture
def empty_catalogue(database):
    """A catalogue with nothing in it."""
    tables = [r["tablename"] for r in database.query(
        "select tablename from pg_tables where schemaname = current_schema() "
        "and tablename <> 'schema_migrations'")]
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
