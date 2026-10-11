"""Converts a World into plain JSON-friendly dicts for the web front end."""

from __future__ import annotations

from typing import Any, Callable

from .tree import Node, Tree
from .world import XY, Agent, Event, Player, World


def _xy(pos: XY | None) -> dict[str, int] | None:
    return None if pos is None else {"x": pos.x, "y": pos.y}


def node_to_dict(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "kind": node.kind.value,
        "label": node.label(),
        "branches": list(node.branches),
        "children": [node_to_dict(c) for c in node.children],
    }


def tree_to_dict(tree: Tree) -> dict[str, Any]:
    return {"name": tree.name, "source": tree.source(), "root": node_to_dict(tree.root)}


def agent_to_dict(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "player": agent.player.name,
        "x": agent.x,
        "y": agent.y,
        "health": agent.health,
        "maxHealth": agent.max_health,
        "power": agent.power,
        "speed": agent.speed,
        "dirt": agent.dirt,
        "food": agent.food,
        "exp": agent.exp,
        "level": agent.level,
        "birth": agent.birth,
        "action": agent.action.activity.value if agent.action else None,
        "tree": agent.tree.name,
        "path": agent.last_path,
        "pathTree": agent.last_path_tree,
        "primary": _xy(agent.primary),
        "secondary": _xy(agent.secondary),
    }


def _hide_thinking(agent: dict[str, Any]) -> dict[str, Any]:
    return {**agent, "tree": None, "path": [], "pathTree": None, "primary": None, "secondary": None}


def event_to_dict(event: Event) -> dict[str, Any]:
    return {"time": event.time, "kind": event.kind, "message": event.message, "agent": event.agent}


def _grid(world: World, attr: str) -> list[list[int | None]]:
    return [[None if (tile := world.tiles[x][y]) is None else getattr(tile, attr)
             for x in range(world.width)] for y in range(world.height)]


def world_to_dict(world: World, include_trees: bool = True,
                  visible: Callable[[Player], bool] | None = None) -> dict[str, Any]:
    """The world for the front end. visible(player) says whether the viewer may see that team's
    trees and what its agents were thinking (their last decision path and remembered positions).
    Other teams' agents are still shown, so the viewer sees what they did but not why."""
    visible = visible or (lambda player: True)
    state: dict[str, Any] = {
        "time": world.time,
        "width": world.width,
        "height": world.height,
        "mode": world.mode,
        "seed": world.seed,
        "maxTurns": world.max_turns,
        "finished": world.finished,
        "outcome": world.outcome,
        "result": world.result,
        # Row-major by y so the client can index tiles[y][x]. None is a hole.
        "dirt": _grid(world, "dirt"),
        "food": _grid(world, "food"),
        "plants": [{"id": p.id, "x": p.pos.x, "y": p.pos.y, "rate": p.rate} for p in world.plants],
        "agents": [agent_to_dict(a) if visible(a.player) else _hide_thinking(agent_to_dict(a))
                   for a in world.agents],
        "players": [
            {
                "name": p.name,
                "slot": p.slot,
                "colour": p.colour,
                "alive": len(p.agents),
                "total": len(p.all_agents),
                "maxAgents": p.max_agents,
                "hidden": not visible(p),
                **({"trees": [tree_to_dict(t) for t in p.trees]} if include_trees and visible(p) else {}),
            }
            for p in world.players
        ],
        "criteria": [c.source() for c in world.criteria],
    }
    return state
