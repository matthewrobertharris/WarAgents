"""Accounts: signing up and in, and who can see and change what."""

import json

from conftest import PASSWORD, sign_in, sign_up

from waragents.web.auth import set_password

TREE = {"name": "mine", "root": {"kind": "OUTPUT", "action": "DEFEND"}}
MAP = {"name": "Bob's map", "mode": "FIXED", "maxAgents": 10, "dirt": [[0, 0]], "food": [[0, 0]],
       "plants": [], "starts": [{"slot": 1, "x": 0, "y": 0}, {"slot": 2, "x": 1, "y": 0}], "criteria": []}


def players(app):
    """The admin, then Alice and Bob, who aren't admins."""
    admin = sign_up(app, "Admin")
    return admin, sign_up(app, "Alice"), sign_up(app, "Bob")


def test_signed_out_requests_are_refused_apart_from_signing_in(app):
    anon = app.test_client()
    assert anon.get("/api/catalogue/maps").status_code == 401
    assert anon.post("/api/games", json={}).status_code == 401
    assert anon.get("/api/me").status_code == 401
    assert anon.get("/api/auth/me").json is None
    assert anon.get("/api/reference").status_code == 200
    assert anon.get("/").status_code == 200


def test_sign_up_sign_in_and_out(app):
    first = sign_up(app, "Admin")
    assert first.get("/api/me").json["admin"] is True
    alice = sign_up(app, "Alice Smith")
    me = alice.get("/api/me").json
    assert (me["id"], me["name"], me.get("admin")) == ("alice-smith", "Alice Smith", None)

    assert app.test_client().post("/api/auth/register", json={"name": "alice smith", "password": PASSWORD}).status_code == 409
    assert app.test_client().post("/api/auth/register", json={"name": "Carol", "password": "short"}).status_code == 422
    assert app.test_client().post("/api/auth/register", json={"name": "!!!", "password": PASSWORD}).status_code == 422
    assert app.test_client().post("/api/auth/login", json={"name": "Alice Smith", "password": "wrong one"}).status_code == 401
    assert app.test_client().post("/api/auth/login", json={"name": "nobody", "password": PASSWORD}).status_code == 401

    again = sign_in(app, "alice-smith")
    assert again.get("/api/auth/me").json["id"] == "alice-smith"
    assert again.post("/api/auth/logout").status_code == 200
    assert again.get("/api/me").status_code == 401


def test_password_hashes_never_leave_the_server(app):
    admin, alice, _ = players(app)
    responses = [alice.get("/api/me"), alice.get("/api/auth/me"), alice.get("/api/catalogue/players"),
                 alice.get("/api/catalogue/players/bob"), admin.get("/api/catalogue/players"),
                 alice.put("/api/catalogue/players/alice", json={"name": "Alice", "colour": "#2f9e44"})]
    for response in responses:
        assert response.status_code == 200
        assert "passwordHash" not in json.dumps(response.json)
    # Saving a profile keeps the password, even though the client never had it.
    assert sign_in(app, "Alice")


def test_changing_your_password(app):
    alice = sign_up(app, "Alice")
    assert alice.put("/api/me/password", json={"current": "nope", "new": "a new password"}).status_code == 403
    assert alice.put("/api/me/password", json={"current": PASSWORD, "new": "short"}).status_code == 422
    assert alice.put("/api/me/password", json={"current": PASSWORD, "new": "a new password"}).status_code == 200
    assert sign_in(app, "Alice", "a new password")


def test_set_password_for_an_old_player(app):
    catalogue = app.extensions["waragents"]["catalogue"]
    catalogue.create("players", {"name": "Matt", "colour": "#1c7ed6", "startTree": None})
    set_password(catalogue, "matt", "matts password", admin=True)
    matt = sign_in(app, "Matt", "matts password")
    assert matt.get("/api/me").json["admin"] is True


def test_trees_belong_to_their_owner(app):
    _, alice, bob = players(app)
    made = bob.post("/api/catalogue/trees", json={**TREE, "owner": "alice"})
    assert made.status_code == 201 and made.json["owner"] == "bob"
    assert bob.post("/api/catalogue/trees", json={**TREE, "name": "two", "owner": None}).json["owner"] == "bob"

    assert "mine" not in {t["id"] for t in alice.get("/api/catalogue/trees").json}
    assert alice.get("/api/catalogue/trees/mine").status_code == 403
    assert alice.put("/api/catalogue/trees/mine", json=TREE).status_code == 403
    assert alice.delete("/api/catalogue/trees/mine").status_code == 403
    # Bob can't give his tree away or make it a default tree.
    moved = bob.put("/api/catalogue/trees/mine", json={**TREE, "owner": None})
    assert moved.status_code == 200 and moved.json["owner"] == "bob"
    # Default trees are for everyone to use and only admins to change.
    assert alice.get("/api/catalogue/trees/defend").status_code == 200
    assert alice.put("/api/catalogue/trees/defend", json={**TREE, "name": "defend"}).status_code == 403


def test_maps_can_be_shared_by_publishing_them(app):
    _, alice, bob = players(app)
    made = bob.post("/api/catalogue/maps", json=MAP).json
    assert made["owner"] == "bob"
    assert alice.get(f"/api/catalogue/maps/{made['id']}").status_code == 403
    assert made["id"] not in {m["id"] for m in alice.get("/api/catalogue/maps").json}

    bob.put(f"/api/catalogue/maps/{made['id']}", json={**MAP, "published": True})
    assert alice.get(f"/api/catalogue/maps/{made['id']}").status_code == 200
    assert made["id"] in {m["id"] for m in alice.get("/api/catalogue/maps").json}
    assert alice.put(f"/api/catalogue/maps/{made['id']}", json=MAP).status_code == 403
    assert alice.put("/api/catalogue/maps/skirmish", json=MAP).status_code == 403


def test_players_only_change_themselves(app):
    _, alice, bob = players(app)
    assert bob.put("/api/catalogue/players/alice", json={"name": "Alice!"}).status_code == 403
    assert bob.post("/api/catalogue/players", json={"name": "Carol"}).status_code == 403
    promoted = bob.put("/api/catalogue/players/bob", json={"name": "Bob", "admin": True})
    assert promoted.status_code == 200
    assert bob.get("/api/me").json.get("admin") is None
    assert alice.delete("/api/catalogue/players/bob").status_code == 403


def game(client, **changes):
    body = {"map": "skirmish", "seed": 3, "teams": [{"slot": 1, "tree": "graze"}, {"slot": 2, "tree": "raid"}],
            **changes}
    return client.post("/api/games", json=body)


def test_games_are_private_to_the_people_in_them(app):
    admin, alice, bob = players(app)
    game_id = game(bob).json["id"]
    assert bob.get(f"/api/games/{game_id}").status_code == 200
    assert alice.get(f"/api/games/{game_id}").status_code == 403
    assert game_id not in {g["id"] for g in alice.get("/api/catalogue/games").json}
    assert game_id in {g["id"] for g in bob.get("/api/catalogue/games").json}

    assert game(bob, teams=[{"slot": 1, "player": "alice"}]).status_code == 403
    assert bob.put(f"/api/catalogue/games/{game_id}", json={}).status_code == 403
    assert alice.delete(f"/api/catalogue/games/{game_id}").status_code == 403
    assert bob.delete(f"/api/catalogue/games/{game_id}").status_code == 200


def test_each_viewer_has_their_own_copy_of_a_game(app):
    admin, _, bob = players(app)
    game_id = game(bob).json["id"]
    bob.post(f"/api/games/{game_id}/step", json={"turns": 5})
    assert admin.post(f"/api/games/{game_id}/step", json={"turns": 2}).json["state"]["time"] == 2
    assert bob.get(f"/api/games/{game_id}").json["state"]["time"] == 5


def test_admins_see_everything(app):
    admin, _, bob = players(app)
    bob.post("/api/catalogue/trees", json=TREE)
    assert admin.get("/api/catalogue/trees/mine").status_code == 200
    assert admin.put("/api/catalogue/trees/mine", json={**TREE, "owner": None}).json["owner"] is None
