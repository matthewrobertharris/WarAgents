"""Writes catalogue/tutorials/*.json, the Training tutorials. Edit the tutorials here and run

    python tools/make_tutorials.py

from the python folder, then pytest (tests/test_tutorials.py checks every model answer completes
its tutorial, and that just defending doesn't).

The designs come from resources/tutorials/*.xlsx. In those sheets, columns B to K are x 0 to 9 and
rows 2 to 11 are y 9 to 0. Pink cells are the agent, green the goal (or a plant), grey walls (holes
here) and blue enemies. Some maps are changed to suit the engine's rules: climbing only costs health
at a height difference of 2, so the hills are steeper than in the sheets.
"""

import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))
from waragents.catalogue import dumps  # noqa: E402

OUT = PYTHON_DIR / "catalogue" / "tutorials"
W = H = 10


# ---- tree helpers --------------------------------------------------------------------------

def do(action, *args):
    return {"kind": "OUTPUT", "action": action, **({"args": list(args)} if args else {})}


def inp(name, *args):
    return {"name": name, "args": list(args)}


def yes_no(question, yes, no):
    return {"kind": "BOOLEAN", "inputs": [question], "children": [yes, no]}


def compare(a, b, less, equal, more):
    return {"kind": "NUMERIC", "inputs": [a, b], "children": [less, equal, more]}


def which_way(position, left, right, up, down, here):
    return {"kind": "POSITION", "inputs": [position], "children": [left, right, up, down, here]}


def tree(name, root):
    return {"name": name, "owner": None, "root": root}


def xy(x, y):
    return {"x": x, "y": y}


def free(direction):
    return inp("IN_BOUNDS", direction)


def first_free(*directions):
    """Move the first of these ways that's on the map (the last is taken regardless)."""
    node = do(f"MOVE_{directions[-1]}")
    for d in reversed(directions[:-1]):
        node = yes_no(free(d), do(f"MOVE_{d}"), node)
    return node


# ---- map helpers ---------------------------------------------------------------------------

def grid(value=0):
    return [[value] * W for _ in range(H)]


def make_map(name, starts, criteria, holes=(), heights=None, food=0, food_at=None, plants=(), max_agents=10):
    dirt, food_grid = grid(0), grid(food)
    for (x, y), h in (heights or {}).items():
        dirt[y][x] = h
    for (x, y), f in (food_at or {}).items():
        food_grid[y][x] = f
    for x, y in holes:
        dirt[y][x] = None
        food_grid[y][x] = None
    return {
        "name": name, "mode": "CLICK", "maxAgents": max_agents,
        "dirt": dirt, "food": food_grid,
        "plants": [{"x": x, "y": y, "rate": r} for x, y, r in plants],
        "starts": [{"slot": s, "x": x, "y": y} for s, x, y in starts],
        "criteria": criteria,
    }


def travel(x, y):
    return [{"type": "TRAVEL_TO", "slot": 1, "x": x, "y": y}]


TUTORIALS = []


def tutorial(id, **fields):
    data = dict(fields)
    for key in ("recommendedAfter", "hints", "concepts"):
        data.setdefault(key, [])
    TUTORIALS.append((id, data))


# ---- movement ------------------------------------------------------------------------------

tutorial(
    "movement-1", name="First steps", track="Movement", order=1, level="Beginner", maxTurns=20,
    brief="Your agent does exactly what its decision tree says, every turn. The simplest tree is a single action. "
          "Open your tree in the Workshop and pick an action from the DO part of the dropdown on its first row.",
    goal="Walk your agent to the flag at x=8, y=5.",
    hints=["The flag is straight to the right of your agent.",
           "A tree with one DO MOVE_RIGHT node does the same thing every turn."],
    concepts=["MOVE_RIGHT"],
    map=make_map("First steps", [(1, 1, 5)], travel(8, 5)),
    solution=tree("first-steps", do("MOVE_RIGHT")))

tutorial(
    "movement-2", name="Into the corner", track="Movement", order=2, level="Beginner", maxTurns=30,
    recommendedAfter=["movement-1"],
    brief="A tree can ask a question and do different things depending on the answer. A BOOLEAN node asks a "
          "yes/no question and has a branch for each answer. IN_BOUNDS asks whether a position is on the map.",
    goal="Reach the top-right corner, x=9, y=9.",
    hints=["Move right while you can, then move up.",
           "Ask IN_BOUNDS RIGHT: if yes, MOVE_RIGHT; if no, MOVE_UP."],
    concepts=["IN_BOUNDS", "MOVE_UP"],
    map=make_map("Into the corner", [(1, 1, 5)], travel(9, 9)),
    solution=tree("into-the-corner", yes_no(free("RIGHT"), do("MOVE_RIGHT"), do("MOVE_UP"))))

GOAL3 = (6, 7)


def towards_primary(right, up, down, left, here=None):
    """Compare your position with PRIMARY: x first, then y."""
    return compare(inp("SELF_X"), inp("GET_X", "PRIMARY"),
                   right,
                   compare(inp("SELF_Y"), inp("GET_Y", "PRIMARY"), up, here or do("DEFEND"), down),
                   left)


tutorial(
    "movement-3", name="Head for a goal", track="Movement", order=3, level="Beginner", maxTurns=30,
    recommendedAfter=["movement-2"],
    brief="Agents can remember a position. SET_PRIMARY stores one as PRIMARY, and inputs such as GET_X PRIMARY read "
          "it back. A NUMERIC node compares two numbers and branches on less than, equal or more than. "
          "Asking about PRIMARY before it's set confuses your agent, so check VALID_POSITION PRIMARY first.",
    goal="Reach the flag at x=6, y=7. Try to build a tree that would reach a flag anywhere.",
    hints=["First turn: SET_PRIMARY to the flag's position (x=6, y=7).",
           "Then compare SELF_X with GET_X PRIMARY: if less, move right; if more, move left.",
           "When the x values are equal, compare SELF_Y with GET_Y PRIMARY to choose up or down."],
    concepts=["SET_PRIMARY", "VALID_POSITION", "SELF_X", "GET_X", "SELF_Y", "GET_Y", "VALUE"],
    map=make_map("Head for a goal", [(1, 1, 5)], travel(*GOAL3)),
    solution=tree("head-for-a-goal", yes_no(
        inp("VALID_POSITION", "PRIMARY"),
        towards_primary(do("MOVE_RIGHT"), do("MOVE_UP"), do("MOVE_DOWN"), do("MOVE_LEFT")),
        do("SET_PRIMARY", xy(*GOAL3)))))

WALL4 = [(4, y) for y in range(3, 8)]
tutorial(
    "movement-4", name="Around a wall", track="Movement", order=4, level="Intermediate", maxTurns=40,
    recommendedAfter=["movement-3"],
    brief="Gaps in the map are holes: your agent can't go there, and IN_BOUNDS says no for them, just like the edge "
          "of the map. A wall stands between your agent and the flag.",
    goal="Get round the wall to the flag at x=7, y=5.",
    hints=["Start with your tree from Head for a goal.",
           "When the way right is blocked, step up (or down) instead, and try right again next turn.",
           "Guard every move with IN_BOUNDS so your agent never walks into the wall."],
    concepts=["IN_BOUNDS", "holes"],
    map=make_map("Around a wall", [(1, 1, 5)], travel(7, 5), holes=WALL4),
    solution=tree("around-a-wall", yes_no(
        inp("VALID_POSITION", "PRIMARY"),
        towards_primary(first_free("RIGHT", "UP", "DOWN"), first_free("UP", "RIGHT", "LEFT"),
                        first_free("DOWN", "RIGHT", "LEFT"), first_free("LEFT", "UP", "DOWN")),
        do("SET_PRIMARY", xy(7, 5)))))

# The corridor maze from the spreadsheet (grey cells), plus (8, 9), (8, 1) and (6, 1). In the
# spreadsheet the wall at x=8 stood on its own, so the corridor looped round it, and a tree that
# kept its left hand on the wall circled that wall forever without reaching the flag. Those three
# walls join it to the edge and leave no loops, so following either wall works.
CORRIDOR = [(8, 9), (8, 1), (6, 1), (1, 9), (2, 9), (6, 9), (1, 8), (2, 8), (4, 8), (6, 8), (8, 8), (1, 7), (2, 7), (4, 7), (6, 7), (8, 7),
            (1, 6), (4, 6), (6, 6), (8, 6), (1, 5), (3, 5), (4, 5), (6, 5), (8, 5), (3, 4), (4, 4), (6, 4), (8, 4),
            (0, 3), (1, 3), (2, 3), (3, 3), (6, 3), (8, 3), (5, 2), (6, 2), (8, 2), (1, 1), (2, 1), (3, 1), (4, 1),
            (5, 1)]

# Keep a wall on your right: try turning right, then straight on, then left, then back.
RIGHT_OF = {"RIGHT": "DOWN", "DOWN": "LEFT", "LEFT": "UP", "UP": "RIGHT"}
LEFT_OF = {v: k for k, v in RIGHT_OF.items()}
BACK = {"RIGHT": "LEFT", "LEFT": "RIGHT", "UP": "DOWN", "DOWN": "UP"}


def follow_right(heading):
    return first_free(RIGHT_OF[heading], heading, LEFT_OF[heading], BACK[heading])


def wall_follower(start):
    """Work out which way the agent is heading from where it was last turn, then keep the wall on
    its right."""
    return yes_no(
        inp("VALID_POSITION", "PREVIOUS"),
        # PREVIOUS to the left means it was moving right, and so on.
        which_way(inp("DIRECTION_TO", "PREVIOUS"),
                  follow_right("RIGHT"), follow_right("LEFT"), follow_right("DOWN"), follow_right("UP"), start),
        start)


tutorial(
    "movement-5", name="Corridor", track="Movement", order=5, level="Intermediate", maxTurns=120,
    recommendedAfter=["movement-4"],
    brief="A winding corridor leads to the flag. One reliable way through a maze: keep a wall on one side and follow "
          "it. PREVIOUS is where your agent was last turn, and a POSITION node with DIRECTION_TO PREVIOUS tells you "
          "which way that was, which tells you which way you're heading.",
    goal="Follow the corridor to the flag at x=9, y=0.",
    hints=["If PREVIOUS is to your left, you're heading right.",
           "Heading right with the wall on your right: try down first, then right, then up, then go back left.",
           "On the first turn there is no PREVIOUS, so check VALID_POSITION PREVIOUS before asking about it."],
    concepts=["PREVIOUS", "DIRECTION_TO", "POSITION nodes", "VALID_POSITION"],
    map=make_map("Corridor", [(1, 0, 9)], travel(9, 0), holes=CORRIDOR),
    solution=tree("corridor", wall_follower(follow_right("RIGHT"))))

U_WALLS = [(x, 7) for x in range(4, 9)] + [(4, y) for y in range(3, 7)] + [(x, 3) for x in range(5, 9)]


def bug_trees(goal, prefix):
    """Two trees: head for the goal, and when a wall's in the way, follow it (wall on the right)
    until back level with the goal and further along than where the wall was hit."""
    go, follow = f"{prefix}-go", f"{prefix}-follow"
    blocked = yes_no(inp("VALID_POSITION", "SECONDARY"), do("CHANGE_TREE", follow), do("SET_SECONDARY", "CURRENT"))
    go_tree = tree(go, yes_no(
        inp("VALID_POSITION", "PRIMARY"),
        towards_primary(yes_no(free("RIGHT"), do("MOVE_RIGHT"), blocked),
                        yes_no(free("UP"), do("MOVE_UP"), blocked),
                        yes_no(free("DOWN"), do("MOVE_DOWN"), blocked),
                        yes_no(free("LEFT"), do("MOVE_LEFT"), blocked)),
        do("SET_PRIMARY", xy(*goal))))
    # At the wall, turn left so the wall is on your right, then follow it.
    walk = yes_no(inp("POSITION_MATCH", "CURRENT", "SECONDARY"),
                  first_free("UP", "DOWN", "LEFT"),
                  wall_follower(follow_right("RIGHT")))
    leave = compare(inp("SELF_X"), inp("GET_X", "SECONDARY"), walk, walk, do("CLEAR_SECONDARY"))
    follow_tree = tree(follow, yes_no(
        inp("VALID_POSITION", "SECONDARY"),
        compare(inp("SELF_Y"), inp("GET_Y", "PRIMARY"), walk, leave, walk),
        do("CHANGE_TREE", go)))
    return go_tree, follow_tree


go6, follow6 = bug_trees((6, 5), "u-bend")
tutorial(
    "movement-6", name="The U-bend", track="Movement", order=6, level="Advanced", maxTurns=150,
    recommendedAfter=["movement-5"],
    brief="The flag is inside a U-shaped wall that opens away from you. Heading straight for it gets you stuck, and "
          "following the wall forever never reaches it. Combine both: head for the flag, follow the wall when it "
          "blocks you, and stop following once you're level with the flag again. A tree can switch to another of "
          "your trees with CHANGE_TREE, so each tree can do one job. SECONDARY can remember where you hit the wall.",
    goal="Reach the flag inside the U at x=6, y=5.",
    hints=["Make two trees: one that heads for the flag, one that follows the wall.",
           "When the way to the flag is blocked: SET_SECONDARY CURRENT, then CHANGE_TREE to your wall-following tree.",
           "In the wall-following tree, when SELF_Y equals GET_Y PRIMARY and you're further right than SECONDARY, "
           "CLEAR_SECONDARY and change back."],
    concepts=["CHANGE_TREE", "SET_SECONDARY", "CLEAR_SECONDARY", "POSITION_MATCH"],
    map=make_map("The U-bend", [(1, 1, 5)], travel(6, 5), holes=U_WALLS),
    solution=go6, extraTrees=[follow6])

go7, follow7 = bug_trees((6, 5), "maze")
tutorial(
    "movement-7", name="The maze", track="Movement", order=7, level="Advanced", maxTurns=200,
    recommendedAfter=["movement-6"],
    brief="The U-bend again, with extra walls in the way. A good wall-following tree copes with whatever the walls "
          "look like.",
    goal="Reach the flag inside the walls at x=6, y=5.",
    hints=["If your U-bend trees really follow walls, they should work here unchanged."],
    concepts=["CHANGE_TREE"],
    map=make_map("The maze", [(1, 1, 5)], travel(6, 5), holes=U_WALLS + [(7, 8), (7, 2)]),
    solution=go7, extraTrees=[follow7])

# ---- food ----------------------------------------------------------------------------------

tutorial(
    "food-1", name="Eat", track="Food", order=1, level="Beginner", maxTurns=10,
    brief="Agents have health. They lose it climbing, carrying things and being attacked, and get it back by eating "
          "food from the tile they're on, a health point per food. An agent at full health can't eat. Your agent "
          "starts hungry, and every tile has food.",
    goal="Eat 10 food.",
    hints=["EAT eats from the tile you're standing on."],
    concepts=["EAT", "health"],
    map=make_map("Eat", [(1, 1, 5)], [{"type": "EAT_FOOD", "slot": 1, "amount": 10}], food=100),
    team={"startHealth": 20},
    solution=tree("eat", do("EAT")))

HILL = {(x, y): max(0, 12 - 2 * (abs(x - 7) + abs(y - 5))) for x in range(W) for y in range(H)}
tutorial(
    "food-2", name="Climbing costs", track="Food", order=2, level="Beginner", maxTurns=40,
    recommendedAfter=["food-1"],
    brief="Stepping up or down a height of 2 costs a health point, and an agent won't make a move that would leave it "
          "with no health. Your agent is small (3 health) and the flag is on top of a steep hill. Every tile has "
          "food, so eat whenever you're low.",
    goal="Climb to the flag at x=7, y=5.",
    hints=["Compare SELF_HEALTH with VALUE 2: if it's less, EAT; otherwise MOVE_RIGHT."],
    concepts=["SELF_HEALTH", "VALUE", "climbing"],
    map=make_map("Climbing costs", [(1, 1, 5)], travel(7, 5), heights=HILL, food=100),
    team={"health": 3},
    solution=tree("climbing-costs", compare(inp("SELF_HEALTH"), inp("VALUE", 2),
                                            do("EAT"), do("MOVE_RIGHT"), do("MOVE_RIGHT"))))

ZIGZAG = {(x, 5): 0 if x % 2 else 2 for x in range(1, 9)}
tutorial(
    "food-3", name="Pack a lunch", track="Food", order=3, level="Intermediate", maxTurns=80,
    recommendedAfter=["food-2"],
    brief="Only your starting tile has food, and the path to the flag goes up and down. Carrying food costs a health "
          "point per move on top of climbing, but you can't eat what you carry: drop it, eat it, and pick up what's "
          "left. LIFT_FOOD picks up to 10 food from your tile, DROP_FOOD puts it all down, and SELF_FOOD says how "
          "much you're carrying.",
    goal="Reach the flag at x=8, y=5.",
    hints=["Not carrying: on a tile with food, EAT until you're full, then LIFT_FOOD. With no food here, move on.",
           "Carrying: move on while you have the health for it (3 or more); otherwise DROP_FOOD so you can eat."],
    concepts=["LIFT_FOOD", "DROP_FOOD", "SELF_FOOD", "HAS_FOOD", "SELF_MAXHEALTH"],
    map=make_map("Pack a lunch", [(1, 1, 5)], travel(8, 5), heights=ZIGZAG, food_at={(1, 5): 100}),
    team={"health": 4},
    solution=tree("pack-a-lunch", compare(
        inp("SELF_FOOD"), inp("VALUE", 0),
        do("DEFEND"),
        yes_no(inp("HAS_FOOD", "CURRENT"),
               compare(inp("SELF_HEALTH"), inp("SELF_MAXHEALTH"), do("EAT"), do("LIFT_FOOD"), do("LIFT_FOOD")),
               do("MOVE_RIGHT")),
        compare(inp("SELF_HEALTH"), inp("VALUE", 3), do("DROP_FOOD"), do("MOVE_RIGHT"), do("MOVE_RIGHT")))))

tutorial(
    "food-4", name="Plants", track="Food", order=4, level="Beginner", maxTurns=60,
    recommendedAfter=["food-1"],
    brief="There's no food anywhere, but plants grow it: every turn a plant puts food on its own tile and a little "
          "on the tiles around it. A plant is a food supply that never runs out. Your agent starts very hungry.",
    goal="Eat 30 food.",
    hints=["PLANT_CURRENT says whether you're standing on a plant.",
           "Walk to the plant, then eat whenever there's food on your tile."],
    concepts=["PLANT_CURRENT", "HAS_FOOD", "plants"],
    map=make_map("Plants", [(1, 1, 5)], [{"type": "EAT_FOOD", "slot": 1, "amount": 30}], plants=[(7, 5, 16)]),
    team={"startHealth": 5},
    solution=tree("plants", yes_no(inp("PLANT_CURRENT"),
                                   yes_no(inp("HAS_FOOD", "CURRENT"), do("EAT"), do("DEFEND")),
                                   do("MOVE_RIGHT"))))

# ---- combat --------------------------------------------------------------------------------

AROUND = [(4, 6), (3, 5), (5, 5), (4, 4)]
ATTACK_ADJACENT = which_way(inp("ENEMY_ADJACENT_POS"), do("ATTACK_LEFT"), do("ATTACK_RIGHT"), do("ATTACK_UP"),
                            do("ATTACK_DOWN"), do("DEFEND"))


def raiders(power, health=100, speed=10, attack=True):
    return [{"slot": 2, "name": "Raiders", "power": power, "health": health, "speed": speed,
             "trees": [tree("raider", ATTACK_ADJACENT if attack else do("DEFEND"))], "startTree": "raider"}]


tutorial(
    "combat-1", name="Defend", track="Combat", order=1, level="Beginner", maxTurns=10,
    brief="Other teams are enemies. An attack takes the attacker's power off the defender's health, but an agent that "
          "chose DEFEND this turn takes only half. Four raiders surround your agent, and together they're strong "
          "enough to kill it in a few turns unless it defends.",
    goal="Survive 5 turns.",
    hints=["Sometimes doing nothing, carefully, is the best move."],
    concepts=["DEFEND"],
    map=make_map("Defend", [(1, 4, 5)] + [(2, x, y) for x, y in AROUND], [{"type": "SURVIVE_TURNS", "turns": 5}]),
    team={"speed": 20}, bots=raiders(power=8),
    solution=tree("defend", do("DEFEND")))

tutorial(
    "combat-2", name="Attack", track="Combat", order=2, level="Beginner", maxTurns=30,
    recommendedAfter=["combat-1"],
    brief="ATTACK_LEFT, ATTACK_RIGHT, ATTACK_UP and ATTACK_DOWN hit the agent next to you that way. "
          "ENEMY_ADJACENT_POS is where an adjacent enemy is, so a POSITION node on it tells you which way to swing. "
          "These raiders only defend.",
    goal="Wipe out the raiders.",
    hints=["POSITION ENEMY_ADJACENT_POS: left → ATTACK_LEFT, right → ATTACK_RIGHT, and so on.",
           "When no enemy is next to you it points at your own tile, the last branch."],
    concepts=["ATTACK_LEFT", "ENEMY_ADJACENT_POS", "POSITION nodes"],
    map=make_map("Attack", [(1, 4, 5)] + [(2, x, y) for x, y in AROUND], [{"type": "ANNIHILATE", "slot": 1}]),
    team={"power": 20, "speed": 20}, bots=raiders(power=1, health=20, attack=False),
    solution=tree("attack", ATTACK_ADJACENT))

tutorial(
    "combat-3", name="High ground", track="Combat", order=3, level="Intermediate", maxTurns=30,
    recommendedAfter=["combat-2"],
    brief="Height matters in a fight. Attacking down from higher ground hits harder: twice as hard from 1 above, three "
          "times from 2. Attacking upwards is weaker. Your agent stands on a mound 2 high; these raiders are as strong "
          "as you, and they fight back.",
    goal="Wipe out the raiders, using the high ground.",
    hints=["Your attack tree from the last tutorial works. Don't step off the mound."],
    concepts=["height in combat"],
    map=make_map("High ground", [(1, 4, 5)] + [(2, x, y) for x, y in AROUND],
                 [{"type": "ANNIHILATE", "slot": 1}], heights={(4, 5): 2}),
    team={"power": 10, "speed": 20}, bots=raiders(power=30, health=30),
    solution=tree("high-ground", ATTACK_ADJACENT))

# ---- dirt ----------------------------------------------------------------------------------

TOWER = {(1, 5): 4, (0, 5): 1, (2, 5): 1, (1, 4): 1, (1, 6): 1}
tutorial(
    "dirt-1", name="Dig your way down", track="Dirt", order=1, level="Beginner", maxTurns=30,
    brief="Height is dirt. Agents can't step to a tile 3 or more higher or lower. LIFT_DIRT picks up to 2 dirt from "
          "the tile you're on, making it lower, and DROP_DIRT puts it back, making your tile higher. "
          "Your agent is stuck on a tower.",
    goal="Get down and walk to the flag at x=7, y=5.",
    hints=["DIRT_VALUE CURRENT is how high your tile is.",
           "If your tile is higher than 2, LIFT_DIRT; otherwise MOVE_RIGHT."],
    concepts=["LIFT_DIRT", "DIRT_VALUE"],
    map=make_map("Dig your way down", [(1, 1, 5)], travel(7, 5), heights=TOWER, food=100),
    solution=tree("dig-down", compare(inp("DIRT_VALUE", "CURRENT"), inp("VALUE", 2),
                                      do("MOVE_RIGHT"), do("MOVE_RIGHT"), do("LIFT_DIRT"))))

PLATEAUS = {(x, y): 0 if x == 4 else 3 for x in range(W) for y in range(H)}
tutorial(
    "dirt-2", name="Bridge the gap", track="Dirt", order=2, level="Intermediate", maxTurns=40,
    recommendedAfter=["dirt-1"],
    brief="A trench 3 deep cuts the map in two, too deep to climb in or out of. You can't drop dirt into a tile you're "
          "not on, but you can lower the edge you're standing on, step down into the trench, and drop the dirt "
          "there to build a step out the other side.",
    goal="Cross the trench to the flag at x=8, y=5.",
    hints=["Not carrying dirt and the tile to your right is the trench (height 0)? If your own tile is higher than 2, "
           "LIFT_DIRT; otherwise step right.",
           "Carrying dirt: step right if the tile there is lower than yours. In the trench, with the far side higher, "
           "DROP_DIRT."],
    concepts=["DROP_DIRT", "SELF_DIRT", "DIRT_VALUE"],
    map=make_map("Bridge the gap", [(1, 1, 5)], travel(8, 5), heights=PLATEAUS, food=100),
    solution=tree("bridge-the-gap", compare(
        inp("SELF_DIRT"), inp("VALUE", 0),
        do("DEFEND"),
        compare(inp("DIRT_VALUE", "RIGHT"), inp("VALUE", 0),
                do("MOVE_RIGHT"),
                compare(inp("DIRT_VALUE", "CURRENT"), inp("VALUE", 2), do("MOVE_RIGHT"), do("MOVE_RIGHT"), do("LIFT_DIRT")),
                do("MOVE_RIGHT")),
        compare(inp("DIRT_VALUE", "RIGHT"), inp("DIRT_VALUE", "CURRENT"),
                do("MOVE_RIGHT"), do("MOVE_RIGHT"),
                compare(inp("DIRT_VALUE", "CURRENT"), inp("VALUE", 0), do("MOVE_RIGHT"), do("DROP_DIRT"), do("MOVE_RIGHT"))))))

# ---- reproduction --------------------------------------------------------------------------

tutorial(
    "reproduction-1", name="Reproduce", track="Reproduction", order=1, level="Beginner", maxTurns=10,
    brief="An agent can REPRODUCE: it splits in two, and the new agent appears on a free tile next to it. Each "
          "keeps half the health, and the new agent follows the same tree from the next turn. A team can only have "
          "so many agents at once.",
    goal="Have 2 agents.",
    hints=["One DO node is enough."],
    concepts=["REPRODUCE", "TEAM_SIZE"],
    map=make_map("Reproduce", [(1, 1, 5)], [{"type": "TEAM_SIZE", "slot": 1, "size": 2}], food=50),
    solution=tree("reproduce", do("REPRODUCE")))


# ---- write -----------------------------------------------------------------------------------

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for tutorial_id, data in TUTORIALS:
        extra = data.pop("extraTrees", [])
        data["solution"] = {**data["solution"], "name": data["solution"]["name"]}
        if extra:
            data["solutionTrees"] = extra
        (OUT / f"{tutorial_id}.json").write_text(dumps(data) + "\n", encoding="utf-8")
    print(f"wrote {len(TUTORIALS)} tutorials to {OUT}")


if __name__ == "__main__":
    main()
