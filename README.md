# WarAgents

WarAgents is a turn-based, multi-agent simulation game written in Java. It is inspired by
[Cells](http://phonons.wordpress.com/2010/06/01/cells-a-massively-multi-agent-python-programming-game/).
In Cells, you program your agents' "minds" in Python. In WarAgents, **designing the agents'
decision trees is the game.**

The author calls it a "0.5 player game". Once a simulation starts, you can't intervene. You
shape the outcome beforehand by building the decision tree that every agent on your team
follows.

## Concept

- A map is a grid of tiles. Each tile has a **height** (dirt) and an amount of **food**, and
  may hold a **plant** (which produces food) and at most one **agent**.
- Each **player** (team) starts with agents that share one or more **decision trees**.
- Each turn, every agent walks its tree from the root to a leaf and performs the resulting
  **action**. Agents act in speed order, and one bubble-sort pass on speed runs each turn.
- A game ends when one of the map's **victory criteria** is met.

### Decision trees

A tree is made of four kinds of node:

| Node       | Inputs              | Children | Branches on                                   |
|------------|---------------------|----------|-----------------------------------------------|
| `OUTPUT`   | none                | 0 (leaf) | Performs an action                            |
| `BOOLEAN`  | 1 boolean input     | 2        | true / false                                  |
| `NUMERIC`  | 2 numeric inputs    | 3        | `<` / `=` / `>`                               |
| `POSITION` | 1 position input    | 5        | left / right / up / down / current            |

If an input throws an error while being evaluated (for example, it asks about an
out-of-bounds tile), the agent becomes `Confused` for that turn.

**Actions (outputs):** move up/down/left/right, attack up/down/left/right, defend, eat, lift/drop
dirt, lift/drop food, reproduce, change tree, set/clear primary and secondary positions (a
simple per-agent memory), plus the system actions `Confused` and `Death`.

**Inputs:**
- *Boolean:* legal move, reproduce legal, in bounds, occupied, valid position, has food, plant,
  ally or enemy, ally/enemy/food/plant adjacent, position match, previous action, ally/enemy
  action, current tree.
- *Numeric:* constant value, random value, time, food and dirt value, x/y, map width/height,
  max food/dirt, team size and max team size, plant rate, number of trees.
- *Position:* direction to, A*, adjacent ally, adjacent enemy.
- *Position arguments* (used by many inputs): `CURRENT`, `LEFT`, `RIGHT`, `UP`, `DOWN`,
  `PREVIOUS`, `PRIMARY`, `SECONDARY`, and an explicit x/y value.

**Victory criteria:** survive N turns, annihilate a player, collect N food, level up, reach a
dirt height at a location, travel to a location, perform an action N times, find a thing.

### Game rules

The main rules are:
- An agent can't move onto a tile whose height differs from its own by more than 2.
- Lifting dirt lowers the tile's height. An agent can carry dirt or food, never both.
- Only food on the ground can be eaten, and food restores health 1:1.
- When an agent reproduces, the child gets half the parent's health.
- A dying agent drops a quarter of its health as food, plus anything it was carrying.

The full design, including future ideas, is in [resources/readme/ideas.txt](resources/readme/ideas.txt).

## Map / game file format

Games are loaded from plain-text `.map` files that use a simple `key=value` format. Trees are
written as S-expressions:

```
height=5
width=5
food=
0 0 0 0 0
... (height rows of width values)
dirt=
0 0 0 0 0
...
plants=0
maxAgents=10
name=test1,speed=10,health=100,power=10,x=2,y=2
tree=default (POSITION DIRECTION_TO LEFT (OUTPUT MOVE_LEFT) (OUTPUT MOVE_RIGHT) (OUTPUT MOVE_UP) (OUTPUT MOVE_DOWN) (OUTPUT DEFEND))
criteria=1
SURVIVE_TURNS 10
mode=CONST
```

- Each `name=` line defines a player. The `tree=` lines directly under it are that player's trees.
- `mode` sets how the simulation advances: `CLICK` (one turn per click), `CONST` (runs
  continuously) or `FIXED` (one turn per second).

`resources/maps/dirt.json` and `dirt.yaml` are mock-ups of a possible replacement map format.
The code doesn't read them yet.

## Project layout

```
src/
  main/        Game (entry point), ProcessTree (tree evaluation), Renderer (map view),
               TreeRenderer (radial tree view), ProcessHistory (end-of-game history dump)
  model/       Map, Tile, Agent, Player, Plant, histories
    tree/      Tree, Node, Output
    input/     Boolean, numeric and position inputs
    output/    Actions (Action base class + one class per action)
    position/  Position arguments (Current, Left, Primary, XYValue, ...)
    criteria/  Victory conditions
  readers/     Parsers for the .map format (one reader interface + impl per concept)
  generators/  Early work on procedural map/player/tree generation (not wired in)
test/          JUnit 4 tests for every output action and position type
resources/
  maps/        Sample maps
  test/        Fixture maps for the unit tests (outputMaps/, positionMaps/)
  readme/      Design notes (ideas.txt), ToDo list, tree-node spreadsheet, radial layout sketch
```

## Running

This is an Eclipse project that targets Java 8 and uses JUnit 4. There's no Maven or Gradle
build. Source folders are `src`, `resources` and `test`.

1. Import the folder into Eclipse as an existing project, or compile `src/` with `javac`.
2. Run `main.Game`. It loads the file named by `Game.FILE` (currently
   `resources\test\basic.map`) and shows a radial view of the first player's first tree.
3. Click the tree window to open the map view, then click the map to advance the simulation
   according to the map's `mode`.
4. When you close the map window, the full agent and tile history is printed to stdout.

The test fixture paths use Windows-style backslashes, so run the tests from the project root
on Windows.

## State of play

Development ran from March 2017 to January 2019 and hasn't been active since.

**Working:**
- The core simulation loop: speed ordering, agent updates, plant growth, per-turn history and
  victory-criteria checks.
- Parsing of the `.map` format, including full decision trees, criteria and mode.
- Evaluation of all four node types, with a `Confused` fallback on errors.
- All the actions listed above, with unit tests for each one's success and failure cases
  (height limits, occupancy, bounds, carrying rules, and so on).
- Unit tests for all position arguments.
- A basic Swing renderer for the map (colour shows height and food; agents are blue, plants
  green) and an experimental radial renderer for trees.
- The main source compiles cleanly on a modern JDK (checked with JDK 21).

**Partial or rough:**
- **Unit tests** exist for outputs and positions. Inputs and criteria have no tests yet.
- **Sample maps are out of date.** Most files in `resources/maps/` use an older
  `players=N` / `decision=` syntax that the current reader doesn't understand. `node.map`
  and the maps under `resources/test/` use the current `tree=` syntax.
- **Generators** (`src/generators`) are a skeleton for procedural generation and aren't used
  by the game.
- **Tree renderer:** the radial layout doesn't handle gaps in the higher levels of a tree well.
- **XP and levelling:** agents gain levels at 2^level XP, but player XP, stat gains and
  level-gated inputs aren't implemented.
- **Configuration** is hard-coded: the map file path and random seed are constants in `Game`.
- The repo tracks build output (`bin/`) and Eclipse workspace metadata (`.metadata/`). Both
  should be removed and added to `.gitignore`.

**Not started** (from [resources/readme/ToDo](resources/readme/ToDo) and the design notes):
- Self, ally and enemy stat inputs, "check" inputs, and a "use sub-tree" input.
- Tree cost and points budgets, and a tree validator that minimises `Confused` outcomes.
- An interactive drag-and-drop tree editor.
- Team special abilities (Fly, Druid, Kamikaze, and so on).
- Game modes: Training, PvE and PvP, plus multiplayer with deterministic replays (seed and
  starting parameters).
- Persistence (a database for maps, players and trees), logging, and system tests for inputs
  and criteria.
- Replacing the `.map` format with JSON or YAML.
