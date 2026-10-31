"""What a team did in a game, counted as the game runs, for the Analytics screen.

Every team (Player) has a TeamStats. The engine adds to it as agents act, fight, eat, are born and
die, and at the end of every turn it notes how many agents the team has and their total health.
Counting changes nothing about the game, so a replay counts the same again: that's how games
played before the counts existed get theirs (analytics.backfill).

Node visits are counted per tree, by node id. A node's id is its place in the tree in pre-order
(the root is 0, then its first branch and everything under it, and so on), the same numbering
the replay viewer uses to highlight an agent's path.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

# Bump when what's counted changes, so analytics.backfill knows to count old games again.
STATS_VERSION = 2


@dataclass
class TeamStats:
    succeeded: Counter = field(default_factory=Counter)  # action name -> times it worked
    failed: Counter = field(default_factory=Counter)  # action name -> times it didn't
    visits: dict[str, Counter] = field(default_factory=dict)  # tree name -> node id -> visits
    confused_at: dict[str, Counter] = field(default_factory=dict)  # tree name -> node id -> errors
    kills: int = 0
    deaths: int = 0
    births: int = 0  # agents born during the game, not the ones the team started with
    damage_dealt: int = 0
    damage_taken: int = 0
    blocks: int = 0  # attacks halved by DEFEND
    food_eaten: int = 0
    agents: list[int] = field(default_factory=list)  # agents alive at the end of each turn, from turn 0
    health: list[int] = field(default_factory=list)  # their total health

    def decided(self, tree: str, path: list[int], action: str, worked: bool) -> None:
        nodes = self.visits.setdefault(tree, Counter())
        nodes.update(path)
        if action == "CONFUSED" and path:
            # The node being evaluated when it went wrong is the last one on the path.
            self.confused_at.setdefault(tree, Counter())[path[-1]] += 1
        (self.succeeded if worked else self.failed)[action] += 1

    def turn_ended(self, agents: int, health: int) -> None:
        self.agents.append(agents)
        self.health.append(health)

    @property
    def confused(self) -> int:
        return self.succeeded["CONFUSED"] + self.failed["CONFUSED"]
