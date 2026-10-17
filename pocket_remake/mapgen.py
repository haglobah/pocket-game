"""Procedural desert world. Pure: the same seed always gives the same world.

The map is 2000 x 1000 tiles, far too big to build eagerly in Python, so
tiles are computed on demand by `tile_at` and cached.
"""

import hashlib
import math
import random
from dataclasses import dataclass
from functools import lru_cache

from .constants import (
    CACTUS,
    CLIFF,
    CLIFF_EDGE,
    DARK_SAND,
    DEAD_BUSH,
    DEEP_WATER,
    GREEN_BUSH,
    MAP_H,
    MAP_W,
    OASIS_RING,
    OASIS_SPACING,
    PALM,
    PORTAL,
    PORTAL_RING,
    RED_BUSH,
    ROCK,
    SAND,
    SPAWN_CLEAR,
    SWIMMABLE,
    WALKABLE,
    WATER,
    WRECK,
    YELLOW_BUSH,
    Point,
)

OASIS_BUSH = {"green": GREEN_BUSH, "red": RED_BUSH, "yellow": YELLOW_BUSH}
SAFE_OASIS = "green"


def seed_from_text(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest(), 16) & 0xFFFFFFFF


# --- wrap-aware geometry -------------------------------------------------


def wrap_delta(d: float, size: int) -> float:
    """Shortest signed distance on a ring of `size`."""
    return (d + size / 2) % size - size / 2


def wrap_point(x: int, y: int) -> Point:
    return Point(x % MAP_W, y % MAP_H)


def offset(a: Point, b: Point) -> tuple[int, int]:
    """Vector from a to b, taking the wrapped short way."""
    return int(wrap_delta(b.x - a.x, MAP_W)), int(wrap_delta(b.y - a.y, MAP_H))


def distance(a: Point, b: Point) -> float:
    dx, dy = offset(a, b)
    return math.hypot(dx, dy)


def chebyshev(a: Point, b: Point) -> int:
    dx, dy = offset(a, b)
    return max(abs(dx), abs(dy))


# --- noise ---------------------------------------------------------------


def _hash(x: int, y: int, seed: int) -> float:
    h = (x * 374761393 + y * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def _value_noise(x: int, y: int, scale: int, seed: int) -> float:
    """Smooth noise in [0, 1). `scale` divides the map size, so it tiles."""
    gx, gy = MAP_W // scale, MAP_H // scale
    fx, fy = x / scale, y / scale
    ix, iy = math.floor(fx), math.floor(fy)
    tx, ty = fx - ix, fy - iy
    sx = tx * tx * (3 - 2 * tx)
    sy = ty * ty * (3 - 2 * ty)
    a = _hash(ix % gx, iy % gy, seed)
    b = _hash((ix + 1) % gx, iy % gy, seed)
    c = _hash(ix % gx, (iy + 1) % gy, seed)
    d = _hash((ix + 1) % gx, (iy + 1) % gy, seed)
    top = a + (b - a) * sx
    bottom = c + (d - c) * sx
    return top + (bottom - top) * sy


ELEVATION_OCTAVES = ((125, 0.45), (50, 0.28), (25, 0.17), (10, 0.10))
CLIFF_LEVEL = 0.66
CLIFF_EDGE_LEVEL = 0.70


def elevation(seed: int, x: int, y: int) -> float:
    return sum(
        w * _value_noise(x, y, s, seed + 101 * i)
        for i, (s, w) in enumerate(ELEVATION_OCTAVES)
    )


def base_tile(seed: int, x: int, y: int) -> int:
    """Terrain before oases, plants and landmarks."""
    e = elevation(seed, x, y)
    if e > CLIFF_EDGE_LEVEL:
        return CLIFF_EDGE
    if e > CLIFF_LEVEL:
        return CLIFF
    if _value_noise(x, y, 8, seed + 999) > 0.62:
        return DARK_SAND
    return SAND


# --- world ---------------------------------------------------------------


@dataclass(frozen=True)
class Oasis:
    center: Point
    radius: int
    kind: str  # "green" (drinkable) | "red" | "yellow" (poisonous)

    @property
    def safe(self) -> bool:
        return self.kind == SAFE_OASIS


@dataclass(frozen=True)
class World:
    seed: int
    spawn: Point
    oases: tuple[Oasis, ...]
    portal: Point
    # Spawn-relative vectors to each landmark. A cliff-free pass is carved
    # along each one, so every landmark is reachable on foot.
    passes: tuple[tuple[int, int], ...]

    def __hash__(self) -> int:
        return self.seed


def nearest(pred, start: Point, limit: int = 200) -> Point:
    """Closest tile (Chebyshev rings) that satisfies `pred(x, y)`."""
    for r in range(limit):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                p = wrap_point(start.x + dx, start.y + dy)
                if pred(p.x, p.y):
                    return p
    return start


def _ring_point(rng: random.Random, center: Point, ring: tuple[int, int]) -> Point:
    angle = rng.uniform(0, 2 * math.pi)
    dist = rng.uniform(*ring)
    return wrap_point(
        round(center.x + math.cos(angle) * dist),
        round(center.y + math.sin(angle) * dist),
    )


def generate(seed: int) -> World:
    center = Point(MAP_W // 2, MAP_H // 2)
    spawn = nearest(lambda x, y: base_tile(seed, x, y) in WALKABLE, center)
    rng = random.Random(seed)

    kinds = ["green", "red", "yellow"]
    rng.shuffle(kinds)
    oases: list[Oasis] = []
    for kind in kinds:
        candidates = []
        while len(candidates) < 24:
            c = _ring_point(rng, spawn, OASIS_RING)
            if all(distance(c, o.center) >= OASIS_SPACING for o in oases):
                candidates.append(c)
        best = min(candidates, key=lambda c: elevation(seed, c.x, c.y))
        oases.append(Oasis(best, rng.randint(4, 6), kind))

    while True:
        guess = _ring_point(rng, spawn, PORTAL_RING)
        if all(distance(guess, o.center) > 25 for o in oases):
            break
    portal = nearest(lambda x, y: base_tile(seed, x, y) in WALKABLE, guess)

    passes = tuple(offset(spawn, p) for p in [o.center for o in oases] + [portal])
    return World(seed, spawn, tuple(oases), portal, passes)


def _near_pass(world: World, sx: int, sy: int) -> bool:
    for vx, vy in world.passes:
        length2 = vx * vx + vy * vy
        t = max(0.0, min(1.0, (sx * vx + sy * vy) / length2))
        if math.hypot(sx - t * vx, sy - t * vy) <= 1.5:
            return True
    return False


def oasis_at(world: World, p: Point, reach: int = 3) -> Oasis | None:
    """The oasis whose water is at or near `p`."""
    for o in world.oases:
        if distance(p, o.center) <= o.radius + reach:
            return o
    return None


@lru_cache(maxsize=500_000)
def tile_at(world: World, x: int, y: int) -> int:
    x %= MAP_W
    y %= MAP_H
    seed = world.seed
    if (x, y) == world.portal:
        return PORTAL
    sx = int(wrap_delta(x - world.spawn.x, MAP_W))
    sy = int(wrap_delta(y - world.spawn.y, MAP_H))
    if -1 <= sx <= 1 and -2 <= sy <= -1:
        return WRECK
    from_spawn = math.hypot(sx, sy)

    for o in world.oases:
        dx = wrap_delta(x - o.center.x, MAP_W)
        dy = wrap_delta(y - o.center.y, MAP_H)
        if abs(dx) > o.radius + 7 or abs(dy) > o.radius + 7:
            continue
        d = math.hypot(dx, dy)
        h = _hash(x, y, seed + 7)
        shore = o.radius + (h - 0.5) * 1.4
        if d <= shore - 2:
            return DEEP_WATER
        if d <= shore:
            return WATER
        h2 = _hash(x, y, seed + 13)
        if d <= o.radius + 2.5:
            return OASIS_BUSH[o.kind] if h2 < 0.5 else SAND
        if d <= o.radius + 7:
            return PALM if h2 < 0.09 and from_spawn >= SPAWN_CLEAR else SAND

    base = base_tile(seed, x, y)
    if from_spawn <= 4:
        return SAND
    if _near_pass(world, sx, sy):
        return SAND if base in (CLIFF, CLIFF_EDGE) else base
    if base in (CLIFF, CLIFF_EDGE) or from_spawn < SPAWN_CLEAR:
        return base

    s = _hash(x, y, seed + 31)
    if s < 0.009:
        return PALM if elevation(seed, x, y) < 0.45 else CACTUS
    if s < 0.016:
        return DEAD_BUSH
    if s < 0.020:
        return ROCK
    return base


def passable(world: World, p: Point) -> bool:
    t = tile_at(world, p.x, p.y)
    return t in WALKABLE or t in SWIMMABLE


def in_water(world: World, p: Point) -> bool:
    return tile_at(world, p.x, p.y) in SWIMMABLE
