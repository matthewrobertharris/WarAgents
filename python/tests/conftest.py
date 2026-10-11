"""Fixtures for the web app tests: an app with its own copy of the bundled catalogue, and clients
signed in as different players."""

import shutil

import pytest

from waragents.web.app import DEFAULT_CATALOGUE, create_app

BUNDLED = {"maps": ["basic", "islands", "skirmish"], "trees": ["defend", "graze", "guard", "raid", "wander"]}
PASSWORD = "correct horse"


@pytest.fixture
def catalogue_dir(tmp_path):
    """A catalogue with the bundled maps and trees. Anything else in python/catalogue (your own
    maps, trees, players and games) is left out."""
    root = tmp_path / "catalogue"
    for kind, ids in BUNDLED.items():
        (root / kind).mkdir(parents=True)
        for item_id in ids:
            shutil.copy(DEFAULT_CATALOGUE / kind / f"{item_id}.json", root / kind)
    return root


@pytest.fixture
def app(catalogue_dir):
    return create_app(catalogue_dir)


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
