"""Helpers shared by the overworld and the dark world. Pure."""

import math
from dataclasses import replace

from . import story
from .commands import Cmd, PlaySound, StopMusic
from .constants import MAP_H, MAP_W, Point
from .mapgen import wrap_delta, wrap_point
from .model import Model, Player, Projectile


def goto(model: Model, state: str, **changes) -> Model:
    return replace(model, state=state, state_timer=0, **changes)


def learn(learned: tuple[str, ...], skill: str) -> tuple[str, ...]:
    return learned if skill in learned else learned + (skill,)


def step(
    p: Player, dx: int, dy: int, can_enter, cost, wrap=True
) -> tuple[Player, bool]:
    """Advance the step timer; start a new step if one is due and wanted.

    `can_enter(point)` says whether a tile is free, `cost(point)` gives the
    frames the step takes. Diagonals slide along an axis when blocked.
    """
    if p.move_cd > 0:
        p = replace(p, move_cd=p.move_cd - 1)
    if p.move_cd > 0 or (dx == 0 and dy == 0):
        return p, False
    p = replace(p, facing=Point(dx, dy), prev=p.pos)
    for cx, cy in dict.fromkeys([(dx, dy), (dx, 0), (0, dy)]):
        if cx == 0 and cy == 0:
            continue
        target = Point(p.pos.x + cx, p.pos.y + cy)
        if wrap:
            target = wrap_point(*target)
        if can_enter(target):
            frames = cost(target)
            return replace(p, pos=target, move_cd=frames, move_len=frames), True
    return p, False


def fpos(p) -> tuple[float, float]:
    """Drawn position: between prev and pos while a step is underway."""
    if p.move_cd <= 0 or p.prev == p.pos:
        return float(p.pos.x), float(p.pos.y)
    t = 1 - p.move_cd / p.move_len
    dx = wrap_delta(p.pos.x - p.prev.x, MAP_W)
    dy = wrap_delta(p.pos.y - p.prev.y, MAP_H)
    return p.prev.x + dx * t, p.prev.y + dy * t


def toward(a: Point, b: Point) -> tuple[int, int]:
    dx = wrap_delta(b.x - a.x, MAP_W)
    dy = wrap_delta(b.y - a.y, MAP_H)
    return (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)


def aim(
    x0: float, y0: float, x1: float, y1: float, speed: float, ttl: int
) -> Projectile:
    dx = wrap_delta(x1 - x0, MAP_W)
    dy = wrap_delta(y1 - y0, MAP_H)
    d = math.hypot(dx, dy) or 1.0
    return Projectile(x0, y0, dx / d * speed, dy / d * speed, ttl)


DEATH_SOUND = {
    story.DROWNED: "drowning",
    story.THIRST: "dehydration",
    story.HUNGER: "starvation",
    story.DARK_DEFEAT: "killed_by_enemy",
}


def die(m: Model, reason: str) -> tuple[Model, list[Cmd]]:
    m = goto(m, "dead", death_reason=reason, bolts=(), thought=None)
    return m, [StopMusic(), PlaySound(DEATH_SOUND.get(reason, "suffocating"))]
