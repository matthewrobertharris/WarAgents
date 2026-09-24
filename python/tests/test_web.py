from fastapi.testclient import TestClient
from helpers import map_text

from waragents.web.app import app

client = TestClient(app)


def test_index_and_static_files():
    assert "WarAgents" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


def test_maps_list_marks_legacy_maps():
    maps = {m["id"]: m for m in client.get("/api/maps").json()}
    assert maps["demo/skirmish"]["error"] is None
    assert "decision=" in maps["java/attack"]["error"]


def test_play_a_bundled_map():
    game = client.post("/api/games", json={"map": "demo/skirmish", "seed": 3}).json()
    assert game["state"]["time"] == 0
    assert {p["name"] for p in game["state"]["players"]} == {"green", "red"}

    stepped = client.post(f"/api/games/{game['id']}/step", json={"turns": 5}).json()
    assert stepped["state"]["time"] == 5

    reset = client.post(f"/api/games/{game['id']}/reset").json()
    assert reset["state"]["time"] == 0

    # The same seed replays the same game.
    again = client.post(f"/api/games/{game['id']}/step", json={"turns": 5}).json()
    assert again["state"]["agents"] == stepped["state"]["agents"]


def test_custom_map_text_and_errors():
    text = map_text(players=[("red", 1, 1, ["t (OUTPUT MOVE_RIGHT)"])], criteria=["SURVIVE_TURNS 2"])
    game = client.post("/api/games", json={"text": text}).json()
    state = client.post(f"/api/games/{game['id']}/step", json={"turns": 10}).json()["state"]
    assert state["finished"] and state["time"] == 2
    assert state["agents"][0]["x"] == 3

    bad = client.post("/api/games", json={"text": text.replace("MOVE_RIGHT", "MOVE_SIDEWAYS")})
    assert bad.status_code == 400
    assert "unknown action 'MOVE_SIDEWAYS'" in bad.json()["detail"]


def test_unknown_game():
    assert client.get("/api/games/nope").status_code == 404


def test_reference_lists_inputs():
    ref = client.get("/api/reference").json()
    names = {i["name"]: i for i in ref["inputs"]}
    assert names["HAS_FOOD"]["args"] == ["position"]
    assert names["SELF_HEALTH"]["kind"] == "numeric"
