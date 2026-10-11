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
when the code changes. Maps, trees, players, games and the rest are saved in `catalogue/`. Use
`--catalogue DIR` (or set `WARAGENTS_CATALOGUE`) to keep them somewhere else.

Run the tests with `pytest`.

### Accounts

Everyone signs in. The first account created on a server is its admin. A player's name is also
their username, and passwords are stored as hashes. Players made before accounts existed have no
password: give them one with

```
python -m waragents.web set-password matt --admin
```

(`--admin` is optional.) Session cookies are signed with `WARAGENTS_SECRET`, or with a key the
server makes once and keeps in `catalogue/.secret`.

Players only see their own trees and the default trees, and only change their own trees and maps.
Maps can be published so other players can use them. A game can be seen by whoever started it
and the players who had a team in it. Admins can see and change everything, and only they see the
Catalogue screen.

## How the game fits together

You learn to build trees in **Training**, refine them in the **Workshop**, and take them into
**Battle** against other players. **History** keeps every game you've played, and each one
replays exactly.

- **Trees cost points.** A decision costs what its inputs cost (most cost 1, some more), and
  each action costs 1. A tree that switches to other trees pays for those too. To go into a
  battle, a tree has to fit your **budget**: 20 points at level 1, and 5 more for each level.
  Nothing is locked: the budget is the only limit.
- **XP and levels.** Agents earn XP for actions that succeed. When a game ends, your agents' XP
  becomes account XP: all of it in Season battles and the first time you complete a tutorial,
  half of it in a Skirmish. Season battles add a bonus for taking part and for your place, and
  tutorials add a bonus by difficulty. Account XP raises your level, which raises your budget.
- **Your default tree** (set on your Account, or from the Workshop) plays for you whenever
  another player picks you to fight. Until it's finished and within budget, nobody can pick you.
- **Battles are decided at once.** The server plays the game through and saves the result. You
  see the result first and can watch the replay whenever you like. Every team in a battle has
  the same agents, so only the trees differ. Other players' trees stay private: in a replay you
  see what their agents did, but not their trees or decision paths.

All the numbers above are in `progression.py`.

## The web app

The top bar has Training, Battle, Workshop, Maps, History, Players and Guide, plus your name and
level (which open your Account). Each screen has its own URL, such as `#/battle`.

- **Home** (`#/`): your level, XP and budget, whether your default tree is ready, a suggested next
  step, and results you haven't looked at yet.
- **Training** (`#/training`): the tutorials, grouped by track (Movement, Food, Combat, Dirt,
  Reproduction). A tutorial's page (`#/training/<id>`) has its goal, an explanation, hints, the
  map, and a model answer you can reveal. **Start my tree** makes your own tree for it
  (`tut-<id>`) and opens it in the Workshop, with a link back. **Run it** plays your tree and opens
  the replay (`#/training/<id>/watch/<game>`), which shows whether you completed it when the replay
  reaches the end (or straight away with **Skip to the result**).
- **Battle** has three tabs:
  - **Skirmish** (`#/battle`): pick a map (system maps, your own, and ones other players
    published), your tree (its cost against your budget is shown), and who fills each other start
    slot: a player whose default tree is ready, or a practice bot playing a default tree.
    **Fight** decides the battle and opens its result. `?map=<id>` and `?opponent=<player>` fill
    the form in.
  - **Season** (`#/season`): ranked battles. Choose a tree and **Find a battle**: the server makes
    a map for 2 to 4 teams and finds opponents whose default tree costs about the same as yours,
    closest in rating first. It shows the leaderboard (everyone, or just your band of 10 levels),
    your rank and rating, and past seasons. Admins start and end seasons here.
  - **Sandbox** (`#/sandbox`): set up any game (map, teams, trees and stats) and watch it play out
    turn by turn. No XP. You can only play as yourself or as teams with default trees.
- **Result** (`#/results/<id>`): every team's place, agents and agent XP, what you earned (and
  your rating change in a Season battle), any level-up, and **Watch replay**.
- **Replay** (`#/play/<id>`, add `?turn=40` to jump ahead): Play/Pause (space bar), Step (right
  arrow), +10, Back (left arrow), −10, End and Restart. Going back replays the game from its seed,
  so it ends up exactly where it was. The default speed comes from the map's `mode`: `CLICK` is 2
  turns a second, `FIXED` is 1 and `CONST` is 25. Darker brown is higher ground, green is food,
  plants are small green markers, flags mark `TRAVEL_TO` goals, and agents are circles in their
  team colour with a health ring. Row y = 0 is at the bottom, so `MOVE_UP` moves an agent up the
  screen. The side panels show the teams, the selected agent, its decision tree and an event log.
- **History** (`#/history`): every game you started or had a team in, newest first, filtered by
  mode, with your place, XP and which results are new.
- **Workshop** (`#/trees`): your trees and the default trees. Default trees open read-only:
  **Duplicate** one to make your own copy. **New tree** starts with an empty root. The editor
  (`#/trees/<id>`) is the collapsible outline with a dropdown for every choice on each row,
  offering only what fits that slot:
  - what the node is: an empty slot, an action (picking one makes the node a DO with that
    action), or BOOLEAN, NUMERIC or POSITION
  - for DO, the action's argument (CHANGE_TREE's tree, SET_PRIMARY's position)
  - for BOOLEAN, NUMERIC and POSITION, the input (two for NUMERIC) of the matching kind, with
    its cost next to its name
  - each input's arguments: a position (or XY_VALUE with x and y), a number, an action or a
    tree name. Tree names come from the trees the owner can use.

  Changing a node's type keeps what still fits: a DO becomes the first branch of a new
  decision, and a decision keeps as many branches as the new type has. Each row's ⋯ menu has:
  - focus, copy, cut, paste (works between trees) and clear
  - **Insert a decision above**: a new BOOLEAN, NUMERIC or POSITION node takes this row's place,
    and the row, with everything under it, becomes the new node's first branch
  - **Swap this branch with** another branch of the same decision, everything under them
    included, for when true and false (say) are the wrong way round
  - **Replace this decision with** one of its branches, the opposite of inserting one

  The side panel has the name (no spaces,
  unique per owner), the tree's cost against your budget with **Make this my default tree**, and
  what's left to fill in (click an entry to jump to it). Changes save themselves, and Ctrl+Z and
  Ctrl+Y undo and redo.
- **Maps** (`#/maps`): your maps, the system maps and published maps, as cards. **New map** starts
  with a single tile. Click a map's preview to open it (`#/maps/<id>`); other people's maps open
  read-only.
  - Click a dashed **+** cell to add a tile there, or drag across several. A new tile takes a
    neighbour's height. **Grow all round** adds a tile on every **+** cell. **Fill to rectangle**
    fills the holes and corners inside the map's edges.
  - Click a tile to select it, drag to select a rectangle, and Shift-click to add to the
    selection. The toolbar under the map sets height and food (sliders, or − and +), plants and
    their growth rate, and start slots, and removes tiles to make holes. Keys: + and − change
    height, Delete removes, Esc deselects.
  - The side panel has the name, speed (`mode`), max agents per team, **Published** (so other
    players can fight on it) and the win conditions, and says whether the map can be played yet.
  - Changes save themselves a moment after you stop. Ctrl+Z and Ctrl+Y undo and redo.

  A map can be saved before it's finished, but it can't be played until it has at least one
  start, and its win conditions only refer to slots and tiles that exist.
- **Account** (`#/account`): your name, colour, default tree and password, your level, and your
  record.
- **Players** (`#/players`): everyone, with their level and whether they can be picked to fight. A
  player's page has the games you've played together and a button to fight them.
- **Guide** (`#/guide`): how the game works, the ways to play, XP and levels, and every input and
  action with its cost. It's built from `/api/reference`, so it always matches the server.
- **Catalogue** (admins only): maps, trees, players and games, with delete. The **Import .map**
  tab converts a Java-format `.map` file into a map and its trees.

Trees are shown as a collapsible outline everywhere. Click ▸ to open a branch. Use **focus** (on
hover) to show one branch on its own, with breadcrumbs back to the root. **Expand all** and
**Collapse all** do what they say. In a game, the path the agent took last turn is highlighted and
opened, and **Follow path** forgets your own opening and closing.

## The catalogue

Everything is JSON, one file per item, in `catalogue/maps`, `trees`, `players`, `games`,
`results`, `tutorials` and `seasons`. An item's id is its file name. `scenario.py` describes the
map, tree and game formats in full; `training.py` and `seasons.py` describe tutorials and seasons.

- **Maps** are the board without teams: `dirt` and `food` grids (row n is y = n), `plants`,
  `starts`, `maxAgents`, `mode` and `criteria`, plus an `owner` (null for a system map) and
  `published`. A map doesn't have to be rectangular: `null` in the grids is a hole, which agents
  treat like the edge of the map (see the Islands map). Each start belongs to a numbered slot,
  and criteria refer to teams by slot.
- **Trees** have a `name`, an `owner` and nested nodes:
  `{"kind": "BOOLEAN", "inputs": [{"name": "HAS_FOOD", "args": ["CURRENT"]}], "children": [...]}`.
  A tree with an owner belongs to that player. A tree with `"owner": null` is a default tree,
  which everyone can use. Tree names are unique per owner. A saved tree can have empty slots
  (`null`) while it's unfinished, but it can't be played until they're filled.
- **Players** are accounts: `{"name": "Matthew", "colour": "#1c7ed6", "created": "...",
  "startTree": "graze", "xp": 350, "training": {...}, "passwordHash": "...", "admin": true}`.
  `startTree` is their default tree, looked up in their own trees and then the defaults. `xp` is
  their account XP and `training` their completed tutorials. Players can't set either.
- **Games** hold a `mode` (`training`, `skirmish`, `season` or `sandbox`), a seed, a copy of the
  map, the teams and their trees, the turn limit (`maxTurns`) and the `rules` version, so
  editing a map or tree later doesn't change how an old game replays. A team's copy holds its
  starting tree plus every tree it can reach with `CHANGE_TREE`. `createdBy` and
  `participants` say whose History it's in.
- **Results** are saved next to a game when it's over, under the same id: why it ended, every
  team's place, and the XP (and rating change) each player got. They're kept apart from the
  game, which must never change.
- **Tutorials** have a goal, an explanation, hints, a map whose win conditions are for slot 1,
  the player's agent stats, any practice opponents with their own trees, and a model answer.
  They're written by `tools/make_tutorials.py`: edit them there and run it.
- **Seasons** have a name, whether they're open, each player's rating, battles and wins, and the
  final standings once ended.

The bundled catalogue holds the Skirmish map and its trees (graze, guard, raid), the Basic map,
an Islands map with holes, two small default trees, `defend` and `wander`, and 17 tutorials.
`wander` is the random walk that the skirmish trees repeat.

## Code layout

```
waragents/
  world.py        World (the Java Map), Tile, Agent, Player, Plant, XY, the turn loop and results
  tree.py         Tree and Node, and decide(): walking a tree to an action
  inputs.py       boolean, numeric and position inputs used by decision nodes
  positions.py    position arguments: LEFT, CURRENT, PRIMARY, XY_VALUE x y, ...
  actions.py      the actions at the leaves: MOVE_*, ATTACK_*, EAT, REPRODUCE, ...
  criteria.py     win conditions
  progression.py  the balance: XP, tree costs, levels and budgets, rewards, ratings
  mapfile.py      the .map parser, used for importing and by the tests
  scenario.py     the catalogue's JSON formats: checking them, tree costs, building a World
  catalogue.py    the JSON file store, tree ownership and setting up new games
  battles.py      playing games through, settling results and XP, setting up a Skirmish
  training.py     tutorials
  seasons.py      seasons: matchmaking, ratings and end-of-season rewards
  mapgen.py       generated maps for Season battles
  serialize.py    World to JSON for the web app
  web/            Flask app: app.py (catalogue and games), auth.py (accounts and who can do
                  what), modes.py (Training, Skirmish, Season, History)
    static/js/    main.js (router), session.js, viewer.js, board.js, treeview.js, cost.js,
                  format.js, api.js, dom.js, screens/*.js
catalogue/        the saved maps, trees, players, games, results, tutorials and seasons
tools/            make_tutorials.py, which writes catalogue/tutorials
tests/            pytest suite
```

The engine has no dependencies. The web app needs Flask.

The tests use the Java project's fixture maps in `../resources/test`, so both versions are
checked against the same cases. `test_outputs.py` and `test_positions.py` port the Java JUnit
tests. `test_engine.py` covers the parser, the turn loop, the criteria and the behaviour changes
listed below, and `test_results.py` covers XP, how games end and placings. `test_auth.py`,
`test_progression.py`, `test_modes.py`, `test_tutorials.py` and `test_season.py` cover accounts,
costs and levels, Skirmish and History, Training (including every tutorial's model answer) and
Seasons with generated maps. `test_web.py` covers the rest of the API.

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
- Agents earn XP for actions that succeed, plus a bonus for a kill and for a `DEFEND` that
  blocks an attack. The amounts are in `progression.py`. The Java version never awarded XP, so
  `SELF_EXP` and `LEVEL_UP` did nothing there.
- A team that loses its last agent is knocked out, but the game goes on while two or more teams
  are left. The last team standing wins. `ANNIHILATE` only ends the game early when the game
  would be over anyway.
- Games have a turn limit (`maxTurns`, 2000 by default). With one team, running out of time is a
  failure. Otherwise the team with the most agents, then the most health, wins.
- A finished game has a `result`: why it ended, the winning slots, and every team's place, agents
  and XP. Ties share a place. Game records also note the `rules` version they were played under.
- Two new win conditions, `EAT_FOOD slot amount` and `TEAM_SIZE slot size`, and a team can start
  with less than full health (`startHealth`). The tutorials use them.
- Every input and action has a points cost (`progression.py`), and trees must fit the player's
  budget to go into battle.
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
