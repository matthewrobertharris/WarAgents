# WarAgents (Python)

A Python port of the WarAgents Java game, with a web app for running and inspecting games. See
the [main README](../README.md) for what the game is.

## Running it

You need Python 3.11 or newer.

```
cd python
python -m venv .venv
.venv\Scripts\activate          # on macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python -m waragents.web          # then open http://127.0.0.1:8000
```

Use `--port` to change the port and `--reload` to restart the server when the code changes.

Run the tests with `pytest`.

## The web app

- **Map list:** pick a bundled map, optionally set a seed, and start a new game. The same map
  and seed always replay the same game.
- **Controls:** Play/Pause (space bar), Step (right arrow), +10 and Reset. The default speed
  comes from the map's `mode`: `CLICK` is 2 turns a second, `FIXED` is 1 and `CONST` is 25.
- **Board:** darker brown is higher ground and green is food. Plants are the small green
  markers, and agents are circles in their team colour with a health ring. Row y = 0 is at the
  bottom, so `MOVE_UP` moves an agent up the screen. Hover over a tile for details, or click an
  agent to select it.
- **Side panels:** the teams, the selected agent's stats, its decision tree with the path it
  took last turn highlighted, and an event log (births, deaths, confusion). Failed actions are
  hidden unless you tick the box.
- **Edit map:** change the map file, including the trees, and run it. Parse errors give a line
  number. A cheat sheet next to the editor lists every node type, input, position, action and
  criterion.
- **Links:** a URL like `/?map=demo/skirmish&seed=3&turn=40` opens that exact game position.

The map list shows the demo maps in `maps/` and the Java version's maps in `../resources`. Most
of the Java sample maps use an old `decision=` syntax that neither version can read any more.
They're listed but greyed out.

## Code layout

```
waragents/
  world.py      World (the Java Map), Tile, Agent, Player, Plant, XY, the turn loop
  tree.py       Tree and Node, and decide(): walking a tree to an action
  inputs.py     boolean, numeric and position inputs used by decision nodes
  positions.py  position arguments: LEFT, CURRENT, PRIMARY, XY_VALUE x y, ...
  actions.py    the actions at the leaves: MOVE_*, ATTACK_*, EAT, REPRODUCE, ...
  criteria.py   win conditions
  mapfile.py    the .map parser
  serialize.py  World to JSON for the web app
  web/          FastAPI app (app.py) and the front end (static/)
maps/           demo maps
tests/          pytest suite
```

The engine (everything except `web/`) has no dependencies.

The tests use the Java project's fixture maps in `../resources/test`, so both versions are
checked against the same cases. `test_outputs.py` and `test_positions.py` port the Java JUnit
tests. `test_engine.py` covers the parser, the turn loop, the criteria and the behaviour changes
listed below. `test_web.py` covers the API.

## Differences from the Java version

The rules and messages are the same, and the ported Java tests pass against the same fixtures.
The changes are:

**Bugs fixed**
- `PREVIOUS` was wrong after an agent's second move, and `SET_PRIMARY CURRENT` made the
  remembered position follow the agent. Both came from sharing one mutable position object.
  Positions are now immutable.
- `ENEMY_ADJACENT`, `ALLY_ADJACENT`, `PLANT_ADJACENT` and `IN_BOUNDS` crashed on empty or
  off-map neighbours, which made the agent `CONFUSED`. They now return false.
- `FOOD_ADJACENT` only saw food on tiles that had an agent on them.
- `ENEMY_ADJACENT_POS` looked for allies. Both `*_ADJACENT_POS` inputs only checked two of the
  four directions.
- `SELF_PREVIOUS_ACTION` was always true. `ALLY_ACTION` and `ENEMY_ACTION` compared the other
  agent's action with this agent's own action instead of the named one.
- `NUMERIC` nodes evaluated their inputs up to four times, so `RANDOM` could change between the
  `<` and `>` checks.
- `MAP_DIRT` had its bounds check inverted, so it always threw an error.
- `FIND_THING` could crash on an empty adjacent tile. Plants had no id, so they couldn't be found.
- The turn loop could skip or repeat agents when one died or was born mid-turn, and crashed when
  no agents were left.

**Deliberate changes**
- Agents born during a turn start acting on the next turn.
- All randomness comes from one seeded generator per game, so games can be replayed.
- The parser reports mistakes with a line number. Examples: an unknown token, a boolean input on
  a `NUMERIC` node, an agent off the map, or two agents on one tile. The Java reader silently
  turned unknown nodes into `DEFEND`. A bare action such as `(DEFEND)` is still accepted as
  shorthand for `(OUTPUT DEFEND)`.
- The game ends when no agents are left.
- New numeric inputs for an agent's own stats: `SELF_HEALTH`, `SELF_MAXHEALTH`, `SELF_POWER`,
  `SELF_SPEED`, `SELF_EXP`, `SELF_DIRT`, `SELF_FOOD`, `SELF_AGE`, `SELF_X` and `SELF_Y`. The Java
  `Option` enum listed these but never implemented them.

**Not ported**
- The Swing renderers, including the radial tree view. The web app replaces them.
- Tile history and `ProcessHistory`, the end-of-game text dump of tile traffic, dirt and food.
  Agent history is ported, because the criteria need it.
- The unused `generators` package.
