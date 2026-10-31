# WarAgents

WarAgents is a turn-based, multi-agent simulation game. It is inspired by
[Cells](http://phonons.wordpress.com/2010/06/01/cells-a-massively-multi-agent-python-programming-game/).
In Cells, you program your agents' "minds" in Python. In WarAgents, **designing the agents'
decision trees is the game.**

The author calls it a "0.5 player game". Once a simulation starts, you can't intervene. You
shape the outcome beforehand by building the decision tree that every agent on your team
follows.

The game is a Python engine plus a Flask web app backed by PostgreSQL. You play in the browser:
sign in, learn to build trees in Training tutorials, refine them in the Workshop within a points
budget that grows as you level up, and fight other players in Skirmish and ranked Season battles,
with every game replayable from History. See [python/README.md](python/README.md) to set it up
and run it.

## Concept

- A map is a grid of tiles. Each tile has a **height** (dirt) and an amount of **food**, and
  may hold a **plant** (which produces food) and at most one **agent**.
- Each **player** (team) starts with agents that share one or more **decision trees**.
- Each turn, every agent walks its tree from the root to a leaf and performs the resulting
  **action**. Agents act in speed order, and one bubble-sort pass on speed runs each turn.
- A game ends when one of the map's **victory criteria** is met, when one team is left, or at
  the turn limit.

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
  max food/dirt, team size and max team size, plant rate, number of trees, and the agent's own
  stats (health, power, speed, XP, age and what it carries).
- *Position:* direction to, A*, adjacent ally, adjacent enemy.
- *Position arguments* (used by many inputs): `CURRENT`, `LEFT`, `RIGHT`, `UP`, `DOWN`,
  `PREVIOUS`, `PRIMARY`, `SECONDARY`, and an explicit x/y value.

Every input and action has a points cost, and a tree has to fit its player's budget to go into
battle. The in-game Guide lists them all with their costs.

**Victory criteria:** survive N turns, annihilate a player, collect N food, eat N food, reach a
team size, level up, reach a dirt height at a location, travel to a location, perform an action
N times, find a thing.

### Game rules

The main rules are:
- An agent can't move onto a tile whose height differs from its own by more than 2.
- Lifting dirt lowers the tile's height. An agent can carry dirt or food, never both.
- Only food on the ground can be eaten, and food restores health 1:1.
- When an agent reproduces, the child gets half the parent's health.
- A dying agent drops a quarter of its health as food, plus anything it was carrying.

The original design, including ideas not built yet, is in
[docs/design/ideas.txt](docs/design/ideas.txt).

## Project layout

```
python/          the game: engine, web app, database schema and tests (see python/README.md)
  content/       the bundled system maps, default trees and tutorials, loaded into the database
docs/
  design/        design notes (ideas.txt), the old ToDo list, tree-node spreadsheet, radial layout sketch
  tutorials/     the tutorial designs (spreadsheets), the basis of python/tools/make_tutorials.py
```

## History

WarAgents began as a Java/Swing program, developed from March 2017 to January 2019. It was ported
to Python in 2026 and the Java code has since been removed. It's in the git history before the
`postgres-backend` branch if you need it. The engine still reads the Java version's `.map` files,
which admins can import from the Catalogue screen, and the Java unit tests' fixture maps live on
in `python/tests/fixtures`. [python/README.md](python/README.md) lists the bugs the port fixed and
the rules it changed.
