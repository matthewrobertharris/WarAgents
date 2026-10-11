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

The web app is a Flask app. Use `--port` to change the port and `--reload` to restart the server
when the code changes. Maps, trees, players and games are saved in `catalogue/`. Use
`--catalogue DIR` (or set `WARAGENTS_CATALOGUE`) to keep them somewhere else.

Run the tests with `pytest`.

## The web app

The home page is a menu of six screens. Each screen has its own URL, such as `#/new`.

- **New game:** pick a map, then the number of teams. Each team gets a start slot, a player
  (optional), a name, a colour, a starting tree and its stats. The map's win conditions are
  shown in words. Conditions about unused slots are left out, and so is "wipe out every other
  team" when only one team plays. Starting the game saves it to the catalogue.
- **Load game:** the saved games, newest first. A game carries on from where you left it while
  the server is running. After a restart, it's rebuilt at turn 0 from its seed and starting
  setup, so it plays out exactly the same way.
- **Game view** (`#/play/<id>`, add `?turn=40` to jump ahead): Play/Pause (space bar), Step
  (right arrow), +10, Back (left arrow), −10 and Reset. Going back rebuilds the game from its
  seed and replays it to the earlier turn, so it ends up exactly where it was. The default speed comes from the map's `mode`: `CLICK` is 2 turns
  a second, `FIXED` is 1 and `CONST` is 25. Darker brown is higher ground, green is food, plants
  are small green markers, and agents are circles in their team colour with a health ring. Row
  y = 0 is at the bottom, so `MOVE_UP` moves an agent up the screen. The side panels show the
  teams, the selected agent, its decision tree and an event log.
- **Decision trees:** every tree grouped by owner, with Edit, Duplicate and Delete. **New tree**
  starts with an empty root. The editor (`#/trees/<id>`) is the collapsible outline with a
  dropdown for every choice on each row, offering only what fits that slot:
  - the node type: empty, DO (an action), BOOLEAN, NUMERIC or POSITION
  - for DO, the action and its argument (CHANGE_TREE's tree, SET_PRIMARY's position)
  - for BOOLEAN, NUMERIC and POSITION, the input (two for NUMERIC) of the matching kind
  - each input's arguments: a position (or XY_VALUE with x and y), a number, an action or a
    tree name. Tree names come from the trees the owner can use.

  Changing a node's type keeps what still fits: a DO becomes the first branch of a new
  decision, and a decision keeps as many branches as the new type has. Each row's ⋯ menu has
  focus, copy, paste (works between trees) and clear. The side panel has the name (no spaces,
  unique per owner) and owner, and lists what's left to fill in. Click an entry to jump to it.
  Changes save themselves, and Ctrl+Z and Ctrl+Y undo and redo.
- **Map editor:** every map as a card with Edit, Rename, Play and Delete. **New map** starts
  with a single tile. Click a map's preview to edit it (`#/maps/<id>`):
  - Click a dashed **+** cell to add a tile there, or drag across several. A new tile takes a
    neighbour's height. **Grow all round** adds a tile on every **+** cell. **Fill to rectangle**
    fills the holes and corners inside the map's edges.
  - Click a tile to select it, drag to select a rectangle, and Shift-click to add to the
    selection. The toolbar under the map sets height and food (sliders, or − and +), plants and
    their growth rate, and start slots, and removes tiles to make holes. Keys: + and − change
    height, Delete removes, Esc deselects.
  - The side panel has the name, speed (`mode`), max agents per team and the win conditions,
    and says whether the map can be played yet.
  - Changes save themselves a moment after you stop. Ctrl+Z and Ctrl+Y undo and redo.

  A map can be saved before it's finished, but it can't be played until it has at least one
  start, and its win conditions only refer to slots and tiles that exist.
- **Players** (top right, as it will become account settings): everyone who plays, with their
  trees, games and when they last played. Add a player at the bottom. A player's page
  (`#/players/<id>`) has their name, colour and starting tree, which save as you change them.
  It also has their trees (with New tree), the games they've played in, and Delete, which also
  deletes the trees they own. **New game** there starts a game with their team first. Choosing a
  player in New game gives the team their colour and starting tree.
- **Catalogue:** maps, trees, players and games, with delete. The **Import .map** tab converts
  a Java-format `.map` file into a map and its trees.

Trees are shown as a collapsible outline, in both the game view and the trees screen. Click ▸
to open a branch. Use **focus** (on hover) to show one branch on its own, with breadcrumbs back
to the root. **Expand all** and **Collapse all** do what they say. In a game, the path the agent
took last turn is highlighted and opened, and **Follow path** forgets your own opening and
closing.

## The catalogue

Everything is JSON, one file per item, in `catalogue/maps`, `trees`, `players` and `games`.
An item's id is its file name. `scenario.py` describes the formats in full.

- **Maps** are the board without teams: `dirt` and `food` grids (row n is y = n), `plants`,
  `starts`, `maxAgents`, `mode` and `criteria`. A map doesn't have to be rectangular: `null` in
  the grids is a hole, which agents treat like the edge of the map (see the Islands map). Each
  start belongs to a numbered slot, and criteria refer to teams by slot.
- **Trees** have a `name`, an `owner` and nested nodes:
  `{"kind": "BOOLEAN", "inputs": [{"name": "HAS_FOOD", "args": ["CURRENT"]}], "children": [...]}`.
  A tree with an owner belongs to that player. A tree with `"owner": null` is a default tree,
  which everyone can use. Tree names are unique per owner. A saved tree can have empty slots
  (`null`) while it's unfinished, but it can't be played until they're filled.
- **Players** are people: `{"name": "Matthew", "colour": "#1c7ed6", "created": "...",
  "startTree": "graze"}`. `startTree` is a tree name, looked up in their own trees and then the
  defaults. A team with a player and no tree starts with it.
- **Games** hold a seed plus a copy of the map, the teams and their trees, so editing a map or
  tree later doesn't change how an old game replays. A team's copy holds its starting tree plus
  every tree it can reach with `CHANGE_TREE`. Those are looked up in the player's own trees
  first, then the defaults.

The bundled catalogue holds the Skirmish map and its trees (graze, guard, raid), the Basic map,
an Islands map with holes, and two small default trees, `defend` and `wander`. `wander` is the
random walk that the skirmish trees repeat.

## Code layout

```
waragents/
  world.py      World (the Java Map), Tile, Agent, Player, Plant, XY, the turn loop
  tree.py       Tree and Node, and decide(): walking a tree to an action
  inputs.py     boolean, numeric and position inputs used by decision nodes
  positions.py  position arguments: LEFT, CURRENT, PRIMARY, XY_VALUE x y, ...
  actions.py    the actions at the leaves: MOVE_*, ATTACK_*, EAT, REPRODUCE, ...
  criteria.py   win conditions
  mapfile.py    the .map parser, used for importing and by the tests
  scenario.py   the catalogue's JSON formats: checking them and building a World from a game
  catalogue.py  the JSON file store, tree ownership and setting up new games
  serialize.py  World to JSON for the web app
  web/          Flask app (app.py) and the front end (static/: index.html, style.css, js/)
    static/js/  main.js (router), board.js, treeview.js, api.js, dom.js, screens/*.js
catalogue/      the saved maps, trees, players and games
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
- Maps can have holes, so they don't have to be rectangular. A hole counts as off the map for
  every input and action. `MAP_WIDTH` and `MAP_HEIGHT` are still the size of the whole grid.
- Maps, trees and teams are separate. A map has numbered start slots, a slot can hold several
  starting agents, and teams and their trees are chosen when a game starts.

**Not ported**
- The Swing renderers, including the radial tree view. The web app replaces them.
- Tile history and `ProcessHistory`, the end-of-game text dump of tile traffic, dirt and food.
  Agent history is ported, because the criteria need it.
- The unused `generators` package.
