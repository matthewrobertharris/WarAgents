from pathlib import Path

from conftest import sign_in

from waragents.catalogue import Catalogue
from waragents.web.app import create_app


def new_game(client, **changes):
    body = {"map": "skirmish", "seed": 3, "teams": [
        {"slot": 1, "tree": "graze", "name": "green"},
        {"slot": 2, "tree": "raid", "name": "red"},
    ], **changes}
    return client.post("/api/games", json=body)


def test_index_and_static_files(client):
    assert "WarAgents" in client.get("/").text
    assert client.get("/static/js/main.js").status_code == 200


def test_bundled_catalogue(client):
    maps = {m["id"]: m for m in client.get("/api/catalogue/maps").json}
    assert maps["skirmish"]["slots"] == [1, 2]
    assert (maps["islands"]["width"], maps["islands"]["height"]) == (15, 9)
    trees = {t["id"]: t for t in client.get("/api/catalogue/trees").json}
    assert {"graze", "guard", "raid", "wander", "defend"} <= set(trees)
    assert all(t["problems"] == [] and t["owner"] is None for t in trees.values())


def test_play_a_game(client):
    response = new_game(client)
    assert response.status_code == 201
    game = response.json
    assert game["state"]["time"] == 0
    assert [p["name"] for p in game["state"]["players"]] == ["green", "red"]
    assert {t["name"] for t in game["state"]["players"][0]["trees"]} == {"graze", "guard"}

    stepped = client.post(f"/api/games/{game['id']}/step", json={"turns": 5}).json
    assert stepped["state"]["time"] == 5
    reset = client.post(f"/api/games/{game['id']}/reset").json
    assert reset["state"]["time"] == 0
    again = client.post(f"/api/games/{game['id']}/step", json={"turns": 5}).json
    assert again["state"]["agents"] == stepped["state"]["agents"]


def test_step_back_replays_to_the_same_state(client):
    game_id = new_game(client).json["id"]
    turns = [client.post(f"/api/games/{game_id}/step").json for _ in range(12)]
    back = client.post(f"/api/games/{game_id}/seek", json={"turn": 11}).json
    assert back["state"] == turns[10]["state"]
    assert back["events"][-1]["time"] <= 11
    forward = client.post(f"/api/games/{game_id}/seek", json={"turn": 12}).json
    assert forward["state"] == turns[11]["state"]
    assert client.post(f"/api/games/{game_id}/seek", json={"turn": -1}).status_code == 422


def test_saved_games_are_listed_and_survive_a_restart(client, catalogue):
    game = new_game(client, name="My game").json
    stepped = client.post(f"/api/games/{game['id']}/step", json={"turns": 8}).json

    games = client.get("/api/catalogue/games").json
    assert [(g["id"], g["name"], g["mapName"]) for g in games] == [(game["id"], "My game", "Skirmish")]
    assert [t["startTree"] for t in games[0]["teams"]] == ["graze", "raid"]

    # A new app on the same catalogue has nothing in memory, so it rebuilds the game from its record.
    restarted = sign_in(create_app(Catalogue(catalogue.db)), "Admin")
    assert restarted.get(f"/api/games/{game['id']}").json["state"]["time"] == 0
    replayed = restarted.post(f"/api/games/{game['id']}/step", json={"turns": 8}).json
    assert replayed["state"]["agents"] == stepped["state"]["agents"]

    assert client.delete(f"/api/catalogue/games/{game['id']}").status_code == 200
    assert client.get(f"/api/games/{game['id']}").status_code == 404


def test_catalogue_crud_and_problems(client):
    player = client.post("/api/catalogue/players", json={"name": "Matt", "colour": "#1c7ed6"})
    assert player.status_code == 201 and player.json["id"] == "matt"
    tree = {"name": "mine", "owner": "matt", "root": None}
    assert client.post("/api/catalogue/trees", json=tree).status_code == 201
    listed = {t["id"]: t for t in client.get("/api/catalogue/trees").json}
    assert listed["mine"]["problems"][0]["message"] == "this slot is empty"

    clash = client.post("/api/catalogue/trees", json=tree)
    assert clash.status_code == 400
    assert "already a tree of matt's" in clash.json["problems"][0]

    updated = client.put("/api/catalogue/trees/mine", json={**tree, "root": {"kind": "OUTPUT", "action": "EAT"}})
    assert updated.json["root"]["action"] == "EAT"
    refused = client.delete("/api/catalogue/players/matt")
    assert refused.status_code == 400 and "still owns" in refused.json["detail"]


def test_create_rename_and_edit_a_map(client):
    draft = {"name": "New map", "mode": "FIXED", "maxAgents": 10, "dirt": [[0]], "food": [[0]],
             "plants": [], "starts": [], "criteria": []}
    created = client.post("/api/catalogue/maps", json=draft)
    assert created.status_code == 201
    made = created.json
    assert (made["id"], made["width"], made["problems"]) == ("new-map", 1, ["the map needs at least one start"])

    # Send back what the server returned, with changes: the summary fields aren't saved.
    edited = {**made, "name": "Renamed", "dirt": [[0, None]], "food": [[0, None]],
              "starts": [{"slot": 1, "x": 0, "y": 0}]}
    saved = client.put("/api/catalogue/maps/new-map", json=edited).json
    assert (saved["name"], saved["width"], saved["slots"], saved["problems"]) == ("Renamed", 2, [1], [])
    stored = client.application.extensions["waragents"]["catalogue"].get("maps", "new-map")
    assert "problems" not in stored and "width" not in stored

    game = client.post("/api/games", json={"map": "new-map", "teams": [{"slot": 1, "tree": "wander"}]})
    assert game.status_code == 201


def test_import_a_map_file(client):
    text = (Path(__file__).resolve().parent / "fixtures" / "basic.map").read_text()
    result = client.post("/api/catalogue/import", json={"text": text, "name": "Basic again"})
    assert result.status_code == 201
    assert result.json["map"] == "basic-again"
    bad = client.post("/api/catalogue/import", json={"text": "height=x", "name": "Bad"})
    assert bad.status_code == 400 and "Line 1" in bad.json["detail"]


def test_bad_requests(client):
    assert client.post("/api/games", json={}).status_code == 422
    assert new_game(client, seed="x").status_code == 422
    assert new_game(client, teams=[{"slot": 9, "tree": "graze"}]).status_code == 400
    assert new_game(client, map="nowhere").status_code == 404
    game = new_game(client).json
    assert client.post(f"/api/games/{game['id']}/step", json={"turns": 0}).status_code == 422
    assert client.post(f"/api/games/{game['id']}/step", json={"turns": 1001}).status_code == 422
    assert client.get("/api/catalogue/spells").status_code == 404


def test_unknown_game(client):
    response = client.get("/api/games/nope")
    assert response.status_code == 404
    assert "No game called 'nope'" in response.json["detail"]


def test_reference_lists_inputs_and_criteria(client):
    ref = client.get("/api/reference").json
    names = {i["name"]: i for i in ref["inputs"]}
    assert names["HAS_FOOD"]["args"] == ["position"]
    assert names["SELF_HEALTH"]["kind"] == "numeric"
    assert ref["nodes"]["NUMERIC"] == {"input": "numeric", "count": 2, "branches": ["<", "=", ">"]}
    assert ref["criteria"]["TRAVEL_TO"] == [["slot", "slot"], ["x", "x"], ["y", "y"]]
