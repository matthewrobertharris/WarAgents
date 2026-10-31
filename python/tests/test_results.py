"""Agent XP, how games end (elimination, last team standing, the turn limit), placings, and
playing a game through on the server."""

import pytest
from helpers import make

from waragents.battles import run_to_end
from waragents.content import seed
from waragents.progression import KILL_EXP, action_exp
from waragents.scenario import RULES_VERSION

DEFEND = ["t (OUTPUT DEFEND)"]


def places(world):
    return {p["name"]: p["place"] for p in world.result["placements"]}


# ---- XP ------------------------------------------------------------------------------


def test_successful_actions_earn_xp_and_failed_ones_dont():
    world = make(players=[("red", 1, 0, ["t (OUTPUT MOVE_LEFT)"])])
    agent = world.agents[0]
    world.step()
    assert agent.exp == action_exp("MOVE_LEFT") == 1
    world.step()  # x=0: off the edge, so the move fails
    assert agent.exp == 1
    assert [s.exp for s in agent.history] == [0, 1, 1]


def test_a_kill_earns_a_bonus():
    world = make(width=2, height=1, players=[("red", 0, 0, ["t (OUTPUT ATTACK_RIGHT)"], {"power": 200}),
                                             ("blue", 1, 0, DEFEND)])
    world.step()
    assert world.agents[0].exp == action_exp("ATTACK_RIGHT") + KILL_EXP


def test_agents_level_up_on_powers_of_two():
    agent = make(players=[("red", 0, 0, DEFEND)]).agents[0]
    agent.gain_exp(5)
    assert agent.level == 3  # passed 2 and 4, not 8


# ---- endings and placings -------------------------------------------------------------


def three_teams(**changes):
    world = make(width=3, height=1, players=[
        ("red", 0, 0, ["t (OUTPUT ATTACK_RIGHT)"], {"power": 200}),
        ("blue", 1, 0, DEFEND),
        ("green", 2, 0, DEFEND),
    ], **changes)
    world.max_turns = 5
    return world


def test_a_knocked_out_team_doesnt_end_a_three_team_game():
    world = three_teams(criteria=["ANNIHILATE red", "ANNIHILATE blue", "ANNIHILATE green"])
    world.step()
    assert [p.name for p in world.players if p.agents] == ["red", "green"]
    assert not world.finished
    assert world.eliminated == {id(world.players[1]): 1}


def test_time_limit_ranks_teams_and_ties_share_a_place():
    world = three_teams()
    while not world.finished:
        world.step()
    assert world.time == 5
    assert world.result["reason"] == "turn-limit"
    assert world.result["winners"] == [1, 3]
    assert places(world) == {"red": 1, "green": 1, "blue": 3}
    assert world.outcome == "Time's up after 5 turns: red and green win on agents and health"


def test_time_limit_tie_break_is_agents_then_health():
    world = make(players=[("red", 0, 0, DEFEND), ("blue", 2, 0, DEFEND, {"health": 50})])
    world.max_turns = 2
    world.step()
    world.step()
    assert world.result["winners"] == [1]
    assert places(world) == {"red": 1, "blue": 2}


def test_one_team_running_out_of_time_has_failed():
    world = make(players=[("red", 0, 0, DEFEND)])
    world.max_turns = 3
    for _ in range(3):
        world.step()
    assert world.finished
    assert world.result["reason"] == "turn-limit"
    assert world.result["winners"] == []


def test_last_team_standing_wins_without_any_criteria():
    world = make(width=2, height=1, players=[("red", 0, 0, ["t (OUTPUT ATTACK_RIGHT)"], {"power": 200}),
                                             ("blue", 1, 0, DEFEND)])
    world.step()
    assert world.outcome == "red is the last team standing"
    assert world.result["reason"] == "last-standing"
    assert world.result["winners"] == [1]
    red, blue = world.result["placements"]
    assert (red["name"], red["place"], red["alive"]) == ("red", 1, 1)
    assert (blue["name"], blue["place"], blue["alive"], blue["eliminated"]) == ("blue", 2, 0, 1)


def test_criteria_name_their_winner():
    world = make(players=[("red", 0, 0, DEFEND), ("blue", 3, 0, ["t (OUTPUT MOVE_LEFT)"])],
                 criteria=["TRAVEL_TO blue 2 0"])
    world.step()
    assert world.result["reason"] == "criteria"
    assert world.result["winners"] == [2]
    assert places(world) == {"blue": 1, "red": 2}


def test_annihilating_the_only_other_team_keeps_the_criterion_wording():
    world = make(width=2, height=1, players=[("red", 0, 0, DEFEND),
                                             ("blue", 1, 0, ["t (OUTPUT ATTACK_LEFT)"], {"power": 200})],
                 criteria=["ANNIHILATE red"])
    world.step()
    assert world.outcome == "Game over: red has no agents left"
    assert world.result["winners"] == [2]


def test_placings_rank_later_eliminations_higher():
    # red kills blue on turn 1 (next to it), then can't reach green: green outlasts blue.
    world = three_teams()
    world.max_turns = None
    world.step()
    world.players[2].agents[0].health = 0  # green dies at the start of its next turn
    world.step()
    assert world.result["reason"] == "last-standing"
    assert places(world) == {"red": 1, "green": 2, "blue": 3}


# ---- whole games on the server ----------------------------------------------------------


@pytest.fixture
def cat(empty_catalogue):
    seed(empty_catalogue, only={"maps": ["skirmish"], "trees": ["graze", "guard", "raid", "wander"]})
    return empty_catalogue


def skirmish(cat, seed=7):
    return cat.new_game("skirmish", [{"slot": 1, "tree": "raid"}, {"slot": 2, "tree": "graze"}], seed)[1]


def test_new_games_record_their_turn_limit_and_rules(cat):
    record = skirmish(cat)
    assert record["maxTurns"] >= 1
    assert record["rules"] == RULES_VERSION


def test_run_to_end_always_finishes_and_replays_exactly(cat):
    record = {**skirmish(cat), "maxTurns": 300}
    first = run_to_end(record)
    second = run_to_end(record)
    assert first.finished and first.time <= 300
    assert first.result == second.result
    assert [e.message for e in first.events] == [e.message for e in second.events]


def test_run_to_end_caps_records_without_a_turn_limit(cat):
    record = skirmish(cat)
    del record["maxTurns"]
    assert run_to_end(record).finished
