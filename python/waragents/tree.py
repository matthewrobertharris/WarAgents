"""Decision trees and how an agent walks them. Ported from model.tree and main.ProcessTree."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .actions import Action, Confused
from .inputs import Input
from .world import Agent, DecisionError, World


class NodeKind(str, Enum):
    OUTPUT = "OUTPUT"
    BOOLEAN = "BOOLEAN"
    NUMERIC = "NUMERIC"
    POSITION = "POSITION"


# For each decision node kind: the kind of input it takes, how many, and its branch labels.
NODE_SHAPES = {
    NodeKind.BOOLEAN: ("boolean", 1, ("true", "false")),
    NodeKind.NUMERIC: ("numeric", 2, ("<", "=", ">")),
    NodeKind.POSITION: ("position", 1, ("left", "right", "up", "down", "current")),
}

CONFUSED = Confused()


@dataclass(eq=False)
class Node:
    id: int
    kind: NodeKind
    depth: int
    inputs: list[Input] = field(default_factory=list)
    children: list[Node] = field(default_factory=list)
    action: Action | None = None

    @property
    def branches(self) -> tuple[str, ...]:
        return NODE_SHAPES[self.kind][2] if self.kind in NODE_SHAPES else ()

    def label(self) -> str:
        if self.kind is NodeKind.OUTPUT:
            return self.action.source()
        return " ".join(i.source() for i in self.inputs)

    def source(self) -> str:
        """This subtree in the map-file syntax."""
        inner = " ".join([self.kind.value, self.label(), *(c.source() for c in self.children)])
        return f"({inner})"


@dataclass(eq=False)
class Tree:
    name: str
    root: Node

    def nodes(self) -> list[Node]:
        out: list[Node] = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            out.append(node)
            stack.extend(reversed(node.children))
        return out

    def source(self) -> str:
        return f"tree={self.name} {self.root.source()}"


def decide(root: Node, agent: Agent, world: World) -> tuple[Action, list[int]]:
    """Walk the tree from root to a leaf. Returns the action and the ids of the nodes visited.

    If an input can't be evaluated (for example it refers to a tile off the map), the agent is
    CONFUSED for this turn.
    """
    node = root
    path: list[int] = []
    try:
        while node.kind is not NodeKind.OUTPUT:
            path.append(node.id)
            node = node.children[_branch(node, agent, world)]
    except DecisionError as e:
        world.log("confused", f"{agent.id} is confused: {e}", agent)
        return CONFUSED, path
    path.append(node.id)
    return node.action, path


def _branch(node: Node, agent: Agent, world: World) -> int:
    if node.kind is NodeKind.BOOLEAN:
        return 0 if node.inputs[0].evaluate(agent, world) else 1
    if node.kind is NodeKind.NUMERIC:
        a = node.inputs[0].evaluate(agent, world)
        b = node.inputs[1].evaluate(agent, world)
        return 0 if a < b else 2 if a > b else 1
    return _direction(agent, node.inputs[0].evaluate(agent, world))


def _direction(agent: Agent, target) -> int:
    """Branch index for a POSITION node: 0 left, 1 right, 2 up, 3 down, 4 current.

    Picks the axis with further to travel. Ties go to left/right.
    """
    dx = target.x - agent.x
    dy = target.y - agent.y
    if dx == 0 and dy == 0:
        return 4
    if abs(dx) >= abs(dy):
        return 0 if dx < 0 else 1
    return 3 if dy < 0 else 2
