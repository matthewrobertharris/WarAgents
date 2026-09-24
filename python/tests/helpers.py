from pathlib import Path

from waragents import World, parse_map

FIXTURES = Path(__file__).resolve().parents[2] / "resources" / "test"


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text()


def load(name: str, seed: int = 1) -> World:
    """Load a map from the shared Java test fixtures, e.g. load("outputMaps/test_eat_fail_noFood.map")."""
    return parse_map(load_text(name), seed=seed)


def map_text(width=5, height=5, players=(), food=0, dirt=0, plants=(), criteria=(), max_agents=10,
             mode="CLICK") -> str:
    """Build a .map file. players are (name, x, y, [tree sources]) with optional stats dict last."""
    def grid(value):
        rows = value if isinstance(value, list) else [[value] * width for _ in range(height)]
        return [" ".join(str(v) for v in row) for row in rows]

    lines = [f"height={height}", f"width={width}", "food=", *grid(food), "dirt=", *grid(dirt),
             f"plants={len(plants)}", *(f"x={x},y={y},rate={r}" for x, y, r in plants),
             f"maxAgents={max_agents}"]
    for name, x, y, trees, *stats in players:
        s = {"speed": 10, "health": 100, "power": 10, **(stats[0] if stats else {})}
        lines.append(f"name={name},speed={s['speed']},health={s['health']},power={s['power']},x={x},y={y}")
        lines.extend(f"tree={t}" for t in trees)
    lines += [f"criteria={len(criteria)}", *criteria, f"mode={mode}"]
    return "\n".join(lines)


def make(seed=1, **kwargs) -> World:
    return parse_map(map_text(**kwargs), seed=seed)


def messages(world: World) -> list[str]:
    """The failure messages logged so far (what the Java version printed to stdout)."""
    return [e.message for e in world.events if e.kind == "fail"]
