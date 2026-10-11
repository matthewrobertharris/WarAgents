"""Generated maps for Season battles.

generate(seed, slots) makes a map for 2 to 4 teams from a seed, so the same seed always gives the
same map. Maps are fair: the terrain, food and plants are symmetric between the start slots (turned
half way round for 2 teams, mirrored both ways for 4, mirrored left to right for 3). Every tile can
be walked to, because neighbouring tiles never differ in height by 3 or more, and holes (in the
lakes style) never cut one start off from another.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from .world import MAX_DIRT, MAX_FOOD

STYLES = {
    # style: (highest dirt, how many holes, how much food)
    "plains": (3, 0.0, 0.4),
    "hills": (8, 0.0, 0.3),
    "highlands": (13, 0.0, 0.25),
    "lakes": (4, 0.12, 0.35),
}
SIZES = {2: (16, 10), 3: (18, 12), 4: (18, 12)}


def _noise(rng: random.Random, width: int, height: int, step: int) -> list[list[float]]:
    """Smooth random values from 0 to 1: random corners every `step` tiles, blended between."""
    cols, rows = width // step + 2, height // step + 2
    corners = [[rng.random() for _ in range(cols)] for _ in range(rows)]
    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            gx, gy = x / step, y / step
            x0, y0 = int(gx), int(gy)
            tx, ty = gx - x0, gy - y0
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            top = corners[y0][x0] * (1 - tx) + corners[y0][x0 + 1] * tx
            bottom = corners[y0 + 1][x0] * (1 - tx) + corners[y0 + 1][x0 + 1] * tx
            row.append(top * (1 - ty) + bottom * ty)
        grid.append(row)
    return grid


def _images(x: int, y: int, width: int, height: int, slots: int) -> list[tuple[int, int]]:
    """The tiles that mirror (x, y) for this many slots, including itself."""
    if slots == 2:
        return [(x, y), (width - 1 - x, height - 1 - y)]
    if slots == 3:
        return [(x, y), (width - 1 - x, y)]
    return [(x, y), (width - 1 - x, y), (x, height - 1 - y), (width - 1 - x, height - 1 - y)]


def _symmetric(grid: list[list[float]], slots: int) -> list[list[float]]:
    height, width = len(grid), len(grid[0])
    return [[sum(grid[j][i] for i, j in _images(x, y, width, height, slots)) / len(_images(x, y, width, height, slots))
             for x in range(width)] for y in range(height)]


def _neighbours(x: int, y: int, width: int, height: int):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if 0 <= x + dx < width and 0 <= y + dy < height:
            yield x + dx, y + dy


def _walkable(dirt: list[list[int]]) -> None:
    """Lower tiles until no neighbours differ in height by 3 or more. Holes are skipped."""
    height, width = len(dirt), len(dirt[0])
    changed = True
    while changed:
        changed = False
        for y in range(height):
            for x in range(width):
                if dirt[y][x] is None:
                    continue
                for nx, ny in _neighbours(x, y, width, height):
                    if dirt[ny][nx] is not None and dirt[y][x] - dirt[ny][nx] > 2:
                        dirt[y][x] = dirt[ny][nx] + 2
                        changed = True


def _reachable(dirt: list[list[int | None]], start: tuple[int, int]) -> set[tuple[int, int]]:
    height, width = len(dirt), len(dirt[0])
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in _neighbours(x, y, width, height):
            if (nx, ny) not in seen and dirt[ny][nx] is not None and abs(dirt[ny][nx] - dirt[y][x]) <= 2:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def _start_tiles(width: int, height: int, slots: int, rng: random.Random) -> list[tuple[int, int]]:
    x = rng.randint(1, max(1, width // 5))
    y = rng.randint(1, max(1, height // 4))
    if slots == 2:
        return [(x, y), (width - 1 - x, height - 1 - y)]
    if slots == 3:
        return [(x, y), (width - 1 - x, y), (width // 2, height - 1 - y)]
    return [(x, y), (width - 1 - x, height - 1 - y), (width - 1 - x, y), (x, height - 1 - y)]


def generate(seed: int, slots: int = 2, style: str | None = None) -> dict[str, Any]:
    """A playable map for this many teams, the same every time for the same seed."""
    if slots not in SIZES:
        raise ValueError("generated maps are for 2 to 4 teams")
    rng = random.Random(seed)
    style = style or rng.choice(sorted(STYLES))
    top, hole_share, food_share = STYLES[style]
    width, height = SIZES[slots]

    terrain = _symmetric(_noise(rng, width, height, rng.choice((3, 4, 5))), slots)
    dirt: list[list[int | None]] = [[min(MAX_DIRT, round(v * top)) for v in row] for row in terrain]
    _walkable(dirt)
    starts = _start_tiles(width, height, slots, rng)

    if hole_share:
        water = _symmetric(_noise(rng, width, height, 3), slots)
        cutoff = sorted(v for row in water for v in row)[int(hole_share * width * height)]
        wet = [[dirt[y][x] if water[y][x] >= cutoff or (x, y) in starts else None
                for x in range(width)] for y in range(height)]
        # Keep the lakes only if every start can still reach every other.
        if set(starts) <= _reachable(wet, starts[0]):
            dirt = wet

    plenty = _symmetric(_noise(rng, width, height, 3), slots)
    food = [[None if dirt[y][x] is None else
             (round(MAX_FOOD * 0.6 * (plenty[y][x] - (1 - food_share)) / food_share)
              if plenty[y][x] > 1 - food_share else 0)
             for x in range(width)] for y in range(height)]

    # Plants in mirrored sets, away from the starts and from each other.
    plants: dict[tuple[int, int], int] = {}
    for _ in range(rng.randint(1, 2)):
        for _attempt in range(50):
            x, y = rng.randrange(width), rng.randrange(height)
            spots = _images(x, y, width, height, slots)
            if all(dirt[j][i] is not None and (i, j) not in plants and (i, j) not in starts for i, j in spots):
                rate = rng.choice((8, 12, 16, 20))
                plants.update({spot: rate for spot in spots})
                break

    return {
        "name": f"Generated {style} #{seed}",
        "mode": "CONST",
        "maxAgents": 10,
        "dirt": dirt,
        "food": food,
        "plants": [{"x": x, "y": y, "rate": r} for (x, y), r in sorted(plants.items())],
        "starts": [{"slot": n + 1, "x": x, "y": y} for n, (x, y) in enumerate(starts)],
        "criteria": [{"type": "ANNIHILATE", "slot": n + 1} for n in range(slots)],
        "generated": {"seed": seed, "style": style},
    }
