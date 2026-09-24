"""WarAgents: a turn-based multi-agent simulation where you program agents with decision trees."""

from .mapfile import MapFormatError, parse_map, parse_tree
from .world import XY, Agent, Event, Player, World

__all__ = ["XY", "Agent", "Event", "MapFormatError", "Player", "World", "parse_map", "parse_tree"]
