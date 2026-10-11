"""Levels, tree budgets and what trees cost."""

from conftest import sign_up

from waragents.progression import (BUDGET_BASE, action_cost, budget_for, input_cost, level_for,
                                   level_summary, xp_for_level)
from waragents.scenario import team_cost, tree_cost


def output(action, *args):
    return {"kind": "OUTPUT", "action": action, **({"args": list(args)} if args else {})}


def boolean(name, args, yes, no):
    return {"kind": "BOOLEAN", "inputs": [{"name": name, "args": args}], "children": [yes, no]}


def tree(root, name="t"):
    return {"name": name, "owner": None, "root": root}


def test_levels_grow_with_xp_and_bring_a_bigger_budget():
    assert [level_for(xp) for xp in (0, 99, 100, 282, 283)] == [1, 1, 2, 2, 3]
    assert all(level_for(xp_for_level(n)) == n for n in range(1, 101))
    assert level_for(10 ** 9) == 100
    assert budget_for(1) == BUDGET_BASE
    assert budget_for(10) > budget_for(2) > budget_for(1)


def test_level_summary():
    summary = level_summary(150)
    assert summary == {"xp": 150, "level": 2, "levelXp": 100, "nextLevelXp": xp_for_level(3),
                       "budget": budget_for(2)}
    assert level_summary(10 ** 9)["nextLevelXp"] is None


def test_a_tree_costs_its_inputs_plus_a_point_per_action():
    root = boolean("HAS_FOOD", ["CURRENT"], output("EAT"),
                   {"kind": "POSITION", "inputs": [{"name": "DIRECTION_TO", "args": ["PRIMARY"]}],
                    "children": [output("MOVE_LEFT"), output("MOVE_RIGHT"), output("MOVE_UP"),
                                 output("MOVE_DOWN"), None]})
    expected = input_cost("HAS_FOOD") + input_cost("DIRECTION_TO") + 5 * action_cost("MOVE_LEFT")
    assert tree_cost(tree(root)) == expected
    assert tree_cost(tree(None)) == 0
    assert input_cost("VALUE") == 0


def test_a_team_pays_once_for_every_tree_it_can_switch_to():
    a = tree(boolean("LEGAL_MOVE", [], output("CHANGE_TREE", "b"), output("DEFEND")), "a")
    b = tree(output("CHANGE_TREE", "a"), "b")
    cost = team_cost(a, {"a": a, "b": b})
    assert cost == {"cost": tree_cost(a) + tree_cost(b), "trees": {"a": 3, "b": 1}}


# ---- through the web app ------------------------------------------------------------------


def test_the_reference_lists_costs(client):
    ref = client.get("/api/reference").json
    inputs = {i["name"]: i for i in ref["inputs"]}
    assert inputs["A_STAR"]["cost"] == input_cost("A_STAR")
    assert all(a["cost"] == 1 for a in ref["actions"])
    trees = {t["id"]: t for t in client.get("/api/catalogue/trees").json}
    assert trees["defend"]["cost"] == 1


def test_me_shows_level_budget_and_default_tree(app):
    alice = sign_up(app, "Alice")
    me = alice.get("/api/me").json
    assert (me["level"], me["xp"], me["budget"]) == (1, 0, BUDGET_BASE)
    assert me["defaultTree"] == {"name": None, "cost": None, "budget": BUDGET_BASE, "ready": False,
                                 "problem": "No tree chosen"}


def test_a_default_tree_must_be_ready_and_within_budget(app):
    alice = sign_up(app, "Alice")
    profile = {"name": "Alice", "colour": "#2f9e44"}
    refused = alice.put("/api/catalogue/players/alice", json={**profile, "startTree": "raid"})
    assert refused.status_code == 400
    assert "costs 97 points and the budget is 20" in refused.json["detail"]

    alice.post("/api/catalogue/trees", json={"name": "half", "root": boolean("LEGAL_MOVE", [], output("EAT"), None)})
    unfinished = alice.put("/api/catalogue/players/alice", json={**profile, "startTree": "half"})
    assert unfinished.status_code == 400 and "Not finished: half" in unfinished.json["detail"]

    assert alice.put("/api/catalogue/players/alice", json={**profile, "startTree": "wander"}).status_code == 200
    assert alice.get("/api/me").json["defaultTree"]["ready"] is True


def test_players_cannot_give_themselves_xp(app):
    sign_up(app, "Admin")
    alice = sign_up(app, "Alice")
    alice.put("/api/catalogue/players/alice", json={"name": "Alice", "xp": 99999})
    assert alice.get("/api/me").json["xp"] == 0


def test_put_me_changes_only_your_own_profile_fields(app):
    sign_up(app, "Admin")
    alice = sign_up(app, "Alice")
    changed = alice.put("/api/me", json={"name": "Alice B", "colour": "#2f9e44", "startTree": "wander",
                                         "xp": 5000, "admin": True, "level": 50})
    assert changed.status_code == 200
    me = changed.json
    assert (me["name"], me["colour"], me["startTree"], me["xp"], me.get("admin")) == ("Alice B", "#2f9e44", "wander", 0, None)
    assert alice.put("/api/me", json={"startTree": "raid"}).status_code == 400
    stored = app.extensions["waragents"]["catalogue"].get("players", "alice")
    assert set(stored) == {"name", "colour", "startTree", "created", "passwordHash"}
