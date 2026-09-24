"""Converts a World into plain JSON-friendly dicts for the web front end."""

from __future__ import annotations

from typing import Any

from .tree import Node, Tree
from .world import XY, Agent, Event, World


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


def event_to_dict(event: Event) -> dict[str, Any]:
    return {"time": event.time, "kind": event.kind, "message": event.message, "agent": event.agent}


def world_to_dict(world: World, include_trees: bool = True) -> dict[str, Any]:
    state: dict[str, Any] = {
        "time": world.time,
        "width": world.width,
        "height": world.height,
        "mode": world.mode,
        "seed": world.seed,
        "finished": world.finished,
        "outcome": world.outcome,
        # Row-major by y so the client can index tiles[y][x].
        "dirt": [[world.tiles[x][y].dirt for x in range(world.width)] for y in range(world.height)],
        "food": [[world.tiles[x][y].food for x in range(world.width)] for y in range(world.height)],
        "plants": [{"id": p.id, "x": p.pos.x, "y": p.pos.y, "rate": p.rate} for p in world.plants],
        "agents": [agent_to_dict(a) for a in world.agents],
        "players": [
            {
                "name": p.name,
                "alive": len(p.agents),
                "total": len(p.all_agents),
                "maxAgents": p.max_agents,
                **({"trees": [tree_to_dict(t) for t in p.trees]} if include_trees else {}),
            }
            for p in world.players
        ],
        "criteria": [c.source() for c in world.criteria],
    }
    return state
