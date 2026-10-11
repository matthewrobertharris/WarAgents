"""The numbers that balance the game: how much XP agents earn, and what levels are worth.

Everything tunable lives here so it can be changed without touching the rules. Changing a number
that affects play (anything an agent can sense, such as its XP) changes how games replay, so bump
scenario.RULES_VERSION when you do.
"""

from __future__ import annotations

# ---- games ---------------------------------------------------------------------------

# A game ends after this many turns if nothing else has ended it. See World._finish_at_time_limit.
DEFAULT_MAX_TURNS = 2000

# ---- agent XP ------------------------------------------------------------------------

# XP an agent earns for each action that succeeds, keyed by Activity name. Actions that only
# change what the agent remembers (SET_PRIMARY, CHANGE_TREE, ...) earn nothing.
ACTION_EXP: dict[str, int] = {
    **{f"MOVE_{d}": 1 for d in ("LEFT", "RIGHT", "UP", "DOWN")},
    **{f"ATTACK_{d}": 2 for d in ("LEFT", "RIGHT", "UP", "DOWN")},
    "EAT": 1,
    "LIFT_FOOD": 1,
    "DROP_FOOD": 1,
    "LIFT_DIRT": 1,
    "DROP_DIRT": 1,
    "REPRODUCE": 5,
}

# Extra XP for the attack that kills an agent, and for a DEFEND that halves an attack.
KILL_EXP = 10
BLOCK_EXP = 1

# An agent reaches level n + 1 once its XP passes AGENT_LEVEL_BASE ** n.
AGENT_LEVEL_BASE = 2


def action_exp(activity: str) -> int:
    return ACTION_EXP.get(activity, 0)


# ---- tree cost -----------------------------------------------------------------------

# Every node in a tree costs points: a decision costs what its inputs cost, and an action (a DO
# node) costs ACTION_COST. A player's trees must fit their budget, which grows with their level.
# Inputs not listed cost DEFAULT_INPUT_COST.
DEFAULT_INPUT_COST = 1
INPUT_COST: dict[str, int] = {
    "VALUE": 0,  # a fixed number, only useful as the other side of a comparison
    "POSITION_MATCH": 2,
    "ALLY_ACTION": 2,
    "ENEMY_ACTION": 2,
    "NUMBER_TREES": 2,
    "ENEMY_ADJACENT_POS": 2,
    "ALLY_ADJACENT_POS": 2,
    "DIRECTION_TO": 3,
    "A_STAR": 3,  # the same step as DIRECTION_TO until it finds paths round obstacles
}
ACTION_COST = 1


def input_cost(name: str) -> int:
    return INPUT_COST.get(name, DEFAULT_INPUT_COST)


def action_cost(name: str) -> int:
    return ACTION_COST


# ---- account levels and budget -------------------------------------------------------

MAX_LEVEL = 100
# Reaching level n takes LEVEL_XP_BASE * (n - 1) ** LEVEL_XP_EXPONENT account XP in total:
# 100 for level 2, about 800 for level 5, 2,700 for level 10 and 98,500 for level 100.
LEVEL_XP_BASE = 100
LEVEL_XP_EXPONENT = 1.5
# The points a player's trees can cost: BUDGET_BASE at level 1, plus BUDGET_PER_LEVEL a level.
BUDGET_BASE = 20
BUDGET_PER_LEVEL = 5


def xp_for_level(level: int) -> int:
    """The total account XP needed to reach a level."""
    return round(LEVEL_XP_BASE * (max(1, level) - 1) ** LEVEL_XP_EXPONENT)


def level_for(xp: int) -> int:
    level = 1
    while level < MAX_LEVEL and xp >= xp_for_level(level + 1):
        level += 1
    return level


def budget_for(level: int) -> int:
    return BUDGET_BASE + BUDGET_PER_LEVEL * (max(1, level) - 1)


def level_summary(xp: int) -> dict:
    """Everything the front end shows about a player's level."""
    level = level_for(xp)
    return {
        "xp": xp,
        "level": level,
        "levelXp": xp_for_level(level),
        "nextLevelXp": None if level >= MAX_LEVEL else xp_for_level(level + 1),
        "budget": budget_for(level),
    }


# ---- account XP from games -------------------------------------------------------------

# Every game gives its players account XP from the XP their agents earned, times a factor for the
# kind of game. Practice teams (no player) get nothing.
MODE_XP_FACTOR = {
    "training": 1.0,  # only the first time a tutorial is completed
    "skirmish": 0.5,
    "season": 1.0,
}
# Season games add a bonus on top: SEASON_PLAY_BONUS for taking part, plus up to SEASON_PLACE_BONUS
# shared out by place (all of it for first, none for last).
SEASON_PLAY_BONUS = 10
SEASON_PLACE_BONUS = 100
# Completing a tutorial for the first time adds a bonus by its difficulty.
TUTORIAL_BONUS = {"Beginner": 25, "Intermediate": 50, "Advanced": 100, "Master": 200}


def season_bonus(place: int, teams: int) -> int:
    if teams < 2:
        return SEASON_PLAY_BONUS
    return SEASON_PLAY_BONUS + round(SEASON_PLACE_BONUS * (teams - place) / (teams - 1))


def account_xp(mode: str, agent_xp: int) -> int:
    """The account XP a player gets for the XP their agents earned in a game of this kind."""
    return round(agent_xp * MODE_XP_FACTOR.get(mode, 0))


# ---- seasons ---------------------------------------------------------------------------------

# Season battles are on generated maps with this turn limit.
SEASON_MAX_TURNS = 600
# Ratings are Elo-style: everyone starts at RATING_START, and after each battle every pair of
# teams counts as a match (a better place wins it), worth up to RATING_K points shared over them.
RATING_START = 1000
RATING_K = 32
# Opponents are picked from players whose default tree costs within this share of your tree's
# cost (widened step by step if too few are in range), closest rating first.
MATCH_COST_RANGE = 0.25
MATCH_COST_WIDEN = 1.5

# At the end of a season, players are ranked within bands of levels (1-10, 11-20, ...), so a
# low-level player competes for rewards with players near their level. A player's reward is a
# share of the XP their next level needs, so it's worth the same to everyone: the top of every
# band gets SEASON_REWARD_TOP of a level, sliding down to SEASON_REWARD_BOTTOM for the last.
# Players need SEASON_MIN_GAMES battles to be rewarded.
SEASON_LEVEL_BAND = 10
SEASON_REWARD_TOP = 0.5
SEASON_REWARD_BOTTOM = 0.05
SEASON_MIN_GAMES = 3


def level_band(level: int) -> int:
    """The band a level is in: 0 for levels 1-10, 1 for 11-20, ..."""
    return (max(1, level) - 1) // SEASON_LEVEL_BAND


def band_label(band: int) -> str:
    return f"Levels {band * SEASON_LEVEL_BAND + 1}-{(band + 1) * SEASON_LEVEL_BAND}"


def season_reward(level: int, rank: int, ranked: int) -> int:
    """XP for finishing at rank (1 is top) of the ranked players in a level band."""
    share = SEASON_REWARD_TOP if ranked <= 1 else (
        SEASON_REWARD_TOP - (SEASON_REWARD_TOP - SEASON_REWARD_BOTTOM) * (rank - 1) / (ranked - 1))
    level_xp = xp_for_level(min(level + 1, MAX_LEVEL)) - xp_for_level(level) or xp_for_level(MAX_LEVEL) // MAX_LEVEL
    return round(share * level_xp)


def rating_changes(ratings: list[float], places: list[int]) -> list[float]:
    """How each team's rating changes after a battle, given everyone's rating and place."""
    n = len(ratings)
    if n < 2:
        return [0.0] * n
    changes = []
    for i in range(n):
        total = 0.0
        for j in range(n):
            if i == j:
                continue
            score = 1.0 if places[i] < places[j] else 0.5 if places[i] == places[j] else 0.0
            expected = 1 / (1 + 10 ** ((ratings[j] - ratings[i]) / 400))
            total += score - expected
        changes.append(RATING_K * total / (n - 1))
    return changes
