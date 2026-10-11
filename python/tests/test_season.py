"""Generated maps, and Seasons: matchmaking, ratings, the leaderboard and end-of-season rewards."""

import pytest
from conftest import sign_up

from waragents.mapgen import STYLES, _reachable, generate
from waragents.progression import (RATING_START, SEASON_MIN_GAMES, SEASON_REWARD_BOTTOM,
                                   SEASON_REWARD_TOP, level_band, rating_changes, season_reward,
                                   xp_for_level)
from waragents.scenario import check_map

# ---- generated maps ------------------------------------------------------------------------


@pytest.mark.parametrize("slots", [2, 3, 4])
@pytest.mark.parametrize("seed", range(12))
def test_generated_maps_are_playable_and_connected(seed, slots):
    data = generate(seed, slots)
    assert check_map(data) == []
    starts = [(s["x"], s["y"]) for s in data["starts"]]
    assert [s["slot"] for s in data["starts"]] == list(range(1, slots + 1))
    assert set(starts) <= _reachable(data["dirt"], starts[0])
    assert data["criteria"] == [{"type": "ANNIHILATE", "slot": n} for n in range(1, slots + 1)]


def test_the_same_seed_gives_the_same_map():
    assert generate(42, 3) == generate(42, 3)
    assert generate(42, 3) != generate(43, 3)


@pytest.mark.parametrize("style", sorted(STYLES))
def test_two_team_maps_are_the_same_both_ways_round(style):
    data = generate(9, 2, style)
    height, width = len(data["dirt"]), len(data["dirt"][0])
    for y in range(height):
        for x in range(width):
            assert data["dirt"][y][x] == data["dirt"][height - 1 - y][width - 1 - x]
            assert data["food"][y][x] == data["food"][height - 1 - y][width - 1 - x]
    plants = {(p["x"], p["y"]): p["rate"] for p in data["plants"]}
    assert plants == {(width - 1 - x, height - 1 - y): r for (x, y), r in plants.items()}


# ---- ratings and rewards ---------------------------------------------------------------------


def test_rating_changes():
    win, loss = rating_changes([1000, 1000], [1, 2])
    assert win == -loss > 0
    assert rating_changes([1000, 1000], [1, 1]) == [0, 0]
    upset, _ = rating_changes([900, 1100], [1, 2])
    expected, _ = rating_changes([1100, 900], [1, 2])
    assert upset > expected  # beating a stronger player is worth more
    assert sum(rating_changes([1000, 1050, 980], [1, 2, 3])) == pytest.approx(0)


def test_season_rewards_are_a_share_of_a_level_for_everyone():
    for level in (1, 10, 55, 99):
        level_xp = xp_for_level(level + 1) - xp_for_level(level)
        assert season_reward(level, 1, 5) == round(SEASON_REWARD_TOP * level_xp)
        assert season_reward(level, 5, 5) == round(SEASON_REWARD_BOTTOM * level_xp)
    assert season_reward(80, 1, 3) > season_reward(8, 1, 3)  # same share, bigger levels
    assert level_band(1) == level_band(10) == 0 and level_band(11) == 1


# ---- through the web app ---------------------------------------------------------------------


@pytest.fixture
def league(app):
    """An admin, and three players with default trees, so there's someone to fight."""
    admin = sign_up(app, "Admin")
    clients = {name: sign_up(app, name) for name in ("Alice", "Bob", "Carol")}
    for client in clients.values():
        assert client.put("/api/me", json={"startTree": "wander"}).status_code == 200
    return {"admin": admin, **clients}


def catalogue(app):
    return app.extensions["waragents"]["catalogue"]


def test_no_season_until_an_admin_starts_one(league):
    alice = league["Alice"]
    assert alice.get("/api/season").json == {"current": None, "past": []}
    assert alice.post("/api/season/battle", json={"tree": "wander"}).status_code == 400
    assert alice.post("/api/season/start", json={}).status_code == 403
    started = league["admin"].post("/api/season/start", json={"name": "Autumn"})
    assert started.status_code == 201 and started.json["name"] == "Autumn"
    assert league["admin"].post("/api/season/start", json={}).status_code == 400  # one at a time


def test_a_season_battle(app, league):
    league["admin"].post("/api/season/start", json={})
    response = league["Alice"].post("/api/season/battle", json={"tree": "wander", "seed": 11})
    assert response.status_code == 201, response.json
    game_id, result = response.json["gameId"], response.json["result"]

    record = catalogue(app).get("games", game_id)
    assert record["mode"] == "season" and record["map"]["name"].startswith("Generated")
    assert record["teams"][0]["player"] == "alice" and len(record["teams"]) >= 2
    assert set(record["participants"]) == {t["player"] for t in record["teams"]}

    rewards = result["rewards"]
    assert set(rewards) == set(record["participants"])
    for player_id, reward in rewards.items():
        assert reward["bonus"] >= 10  # the Season bonus
        assert reward["rating"]["before"] == RATING_START

    season = league["Alice"].get("/api/season").json["current"]
    assert season["me"]["games"] == 1
    assert {r["player"] for r in season["leaderboard"]} == set(record["participants"])
    assert [r["rank"] for r in season["leaderboard"]] == list(range(1, len(season["leaderboard"]) + 1))
    ratings = sorted(r["rating"] for r in season["leaderboard"])
    assert sum(ratings) == pytest.approx(RATING_START * len(ratings), abs=0.5)


def test_season_battles_need_a_ready_tree_and_opponents(app, league):
    league["admin"].post("/api/season/start", json={})
    refused = league["Alice"].post("/api/season/battle", json={"tree": "raid"})
    assert refused.status_code == 400 and "isn't ready" in refused.json["detail"]
    for name in ("Bob", "Carol"):
        league[name].put("/api/me", json={"startTree": None})
    catalogue(app).update("players", "admin", {**catalogue(app).get("players", "admin"), "startTree": None})
    lonely = league["Alice"].post("/api/season/battle", json={"tree": "wander"})
    assert lonely.status_code == 400 and "no one to fight" in lonely.json["detail"]


def test_ending_a_season_rewards_each_level_band(app, league):
    admin = league["admin"]
    season_id = admin.post("/api/season/start", json={}).json["id"]
    for seed in range(SEASON_MIN_GAMES + 1):
        assert league["Alice"].post("/api/season/battle", json={"tree": "wander", "seed": seed}).status_code == 201
    xp_before = league["Alice"].get("/api/me").json["xp"]

    assert league["Alice"].post(f"/api/season/{season_id}/end").status_code == 403
    ended = admin.post(f"/api/season/{season_id}/end").json
    assert ended["status"] == "closed"
    band = ended["standings"][0]
    alice = next(p for p in band["players"] if p["player"] == "alice")
    assert alice["bandRank"] is not None and alice["reward"] > 0
    assert league["Alice"].get("/api/me").json["xp"] == xp_before + alice["reward"]
    unranked = [p for p in band["players"] if p["games"] < SEASON_MIN_GAMES]
    assert all(p["reward"] == 0 and p["bandRank"] is None for p in unranked)

    after = league["Alice"].get("/api/season").json
    assert after["current"] is None and after["past"][0]["id"] == season_id
    assert admin.post(f"/api/season/{season_id}/end").status_code == 400
