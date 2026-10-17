"""The Dark Pocket World: a walled arena with a four-part boss. Pure."""

import math
import random
from dataclasses import replace

from . import story
from .commands import Cmd, PlayMusic, PlaySound, StopMusic
from .common import aim, die, fpos, goto, step
from .constants import (
    BOSS_FIRE_EVERY,
    BOSS_SHOT_SPEED,
    COMPANION_EVERY,
    COMPANION_RANGE,
    DARK_FLOOR,
    DARK_IFRAMES,
    DARK_WALL,
    PUNCH_COOLDOWN,
    PUNCH_RANGE,
    STEP_LAND,
    WIZARD_FOLLOW_EVERY,
    Point,
)
from .messages import Msg, Punch, Tick
from .model import BossPart, Dark, Minion, Model, Player, Zap

__all__ = ["ARENA_START", "BossPart", "Minion", "enter_dark", "update_dark"]

ARENA_W = 48
ARENA_H = 64
ARENA_CENTER = Point(ARENA_W // 2, ARENA_H // 2)
ARENA_START = Point(ARENA_CENTER.x, ARENA_CENTER.y + 10)
BOSS = Point(ARENA_CENTER.x, ARENA_CENTER.y - 20)  # head's top-left anchor

# 2x2 pillars: cover from the head's shots
PILLARS = tuple(
    Point(x, y) for x, y in [(9, 22), (37, 22), (9, 40), (37, 40), (16, 31), (30, 31)]
)

MINION_KINDS = {
    # kind: (hp, move delay, count)
    "squid": (2, 45, 2),
    "squid_small": (1, 35, 3),
    "scorpion": (3, 55, 2),
    "golem": (4, 70, 2),
}


def arena_tile(x: int, y: int) -> int:
    if x <= 0 or y <= 0 or x >= ARENA_W - 1 or y >= ARENA_H - 1:
        return DARK_WALL
    for p in PILLARS:
        if p.x <= x < p.x + 2 and p.y <= y < p.y + 2:
            return DARK_WALL
    return DARK_FLOOR


def make_parts() -> tuple[BossPart, ...]:
    bx, by = BOSS
    return (
        BossPart("wings", bx - 5, by - 4, 10, 4, 3, 3),
        BossPart("left_arm", bx - 5, by, 3, 4, 3, 3),
        BossPart("head", bx - 2, by, 4, 4, 5, 5),
        BossPart("right_arm", bx + 2, by, 3, 4, 3, 3),
    )


def spawn_minions(seed: int, parts) -> tuple[Minion, ...]:
    rng = random.Random(seed ^ 0x5EED)
    taken: set[Point] = set()
    minions = []
    for kind, (hp, delay, count) in MINION_KINDS.items():
        for _ in range(count):
            while True:
                p = Point(BOSS.x + rng.randint(-20, 20), BOSS.y + rng.randint(-6, 34))
                if (
                    arena_tile(*p) == DARK_FLOOR
                    and p not in taken
                    and math.dist(p, ARENA_START) > 10
                    and not any(part.contains(p) for part in parts)
                ):
                    break
            taken.add(p)
            minions.append(Minion(kind, p, p, hp, delay + rng.randint(0, delay)))
    return tuple(minions)


def enter_dark(m: Model) -> tuple[Model, list[Cmd]]:
    parts = make_parts()
    companion = None
    if m.wizard is not None and m.wizard.mode == "follow":
        at = Point(ARENA_START.x - 1, ARENA_START.y + 1)
        companion = replace(m.wizard, pos=at, prev=at, line="", timer=0)
    d = Dark(parts=parts, minions=spawn_minions(m.seed, parts), companion=companion)
    player = Player(pos=ARENA_START, prev=ARENA_START, facing=Point(0, -1))
    m = goto(m, "dark_play", dark=d, player=player, bolts=(), thought=None)
    return m, [StopMusic(), PlaySound("portal"), PlayMusic("boss")]


def head_shielded(d: Dark) -> bool:
    return any(p.alive for p in d.parts if p.name in ("left_arm", "right_arm"))


def blocked(d: Dark, t: Point, ignore=None) -> bool:
    if arena_tile(*t) != DARK_FLOOR:
        return True
    if any(p.alive and p.contains(t) for p in d.parts):
        return True
    return any(mi.pos == t for mi in d.minions if mi is not ignore)


def update_dark(m: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Punch():
            return _punch(m)
        case Tick(dx=dx, dy=dy):
            return _tick(m, dx, dy)
    return m, []


def _punch(m: Model) -> tuple[Model, list[Cmd]]:
    d = m.dark
    if d.punch_cd > 0:
        return m, []
    d = replace(d, punch_cd=PUNCH_COOLDOWN, punch_anim=8)
    p = m.player
    cmds: list[Cmd] = [PlaySound("punch")]
    for reach in range(1, PUNCH_RANGE + 1):
        t = Point(p.pos.x + p.facing.x * reach, p.pos.y + p.facing.y * reach)
        d, hit, c = _damage_at(d, t)
        cmds += c
        if hit or arena_tile(*t) != DARK_FLOOR:
            break
    return replace(m, dark=d), cmds


def _damage_at(d: Dark, t: Point) -> tuple[Dark, bool, list[Cmd]]:
    for i, mi in enumerate(d.minions):
        if mi.pos == t and mi.hp > 0:
            mi = replace(mi, hp=mi.hp - 1, flash=10)
            return (
                replace(d, minions=d.minions[:i] + (mi,) + d.minions[i + 1 :]),
                True,
                [],
            )
    for i, part in enumerate(d.parts):
        if part.alive and part.contains(t):
            if part.name == "head" and head_shielded(d):
                return d, True, [PlaySound("tink")]
            part = replace(part, hp=part.hp - 1, flash=10)
            parts = d.parts[:i] + (part,) + d.parts[i + 1 :]
            cmds = [PlaySound("boss_break")] if not part.alive else []
            return replace(d, parts=parts), True, cmds
    return d, False, []


def _hurt(d: Dark) -> tuple[Dark, list[Cmd]]:
    if d.iframes > 0:
        return d, []
    return replace(d, hp=d.hp - 1, iframes=DARK_IFRAMES), [PlaySound("hit")]


def _tick(m: Model, dx: int, dy: int) -> tuple[Model, list[Cmd]]:
    d = m.dark
    cmds: list[Cmd] = []
    p, moved = step(
        m.player, dx, dy, lambda t: not blocked(d, t), lambda t: STEP_LAND, wrap=False
    )
    if moved:
        cmds.append(PlaySound("step"))

    d = replace(
        d,
        iframes=max(0, d.iframes - 1),
        punch_cd=max(0, d.punch_cd - 1),
        punch_anim=max(0, d.punch_anim - 1),
        parts=tuple(replace(pt, flash=max(0, pt.flash - 1)) for pt in d.parts),
        zaps=tuple(replace(z, age=z.age + 1) for z in d.zaps if z.age < 8),
    )
    px, py = fpos(p)

    # Boss head: aimed shots
    head = next(pt for pt in d.parts if pt.name == "head")
    if head.alive:
        cd = d.fire_cd - 1
        if cd <= 0:
            hx, hy = head.x + head.w / 2 - 0.5, head.y + head.h - 0.5
            shot = aim(hx, hy, px, py, BOSS_SHOT_SPEED, 300)
            d = replace(d, shots=d.shots + (shot,))
            cmds.append(PlaySound("boss_fire"))
            cd = BOSS_FIRE_EVERY
        d = replace(d, fire_cd=cd)

    shots = []
    for s in d.shots:
        s = replace(s, x=s.x + s.vx, y=s.y + s.vy, ttl=s.ttl - 1)
        if abs(s.x - px) < 0.6 and abs(s.y - py) < 0.6:
            d, c = _hurt(d)
            cmds += c
        elif s.ttl > 0 and arena_tile(round(s.x), round(s.y)) == DARK_FLOOR:
            shots.append(s)
    d = replace(d, shots=tuple(shots))

    # Minions: chase, and strike when adjacent
    current = list(d.minions)
    for i, mi in enumerate(current):
        if mi.hp <= 0:
            continue
        mi = replace(
            mi, move_cd=mi.move_cd - 1, flash=max(0, mi.flash - 1), prev=mi.pos
        )
        if mi.move_cd <= 0:
            mi = replace(mi, move_cd=MINION_KINDS[mi.kind][1])
            gap = max(abs(mi.pos.x - p.pos.x), abs(mi.pos.y - p.pos.y))
            if gap <= 1:
                d, c = _hurt(d)
                cmds += c
            else:
                mi = _chase(replace(d, minions=tuple(current)), mi, current[i], p.pos)
        current[i] = mi
    d = replace(d, minions=tuple(current))

    d, c = _companion_tick(d, p)
    cmds += c
    alive = tuple(mi for mi in d.minions if mi.hp > 0)
    if len(alive) < len(d.minions):
        cmds.append(PlaySound("killed_by_enemy"))
    m = replace(m, player=p, dark=replace(d, minions=alive))

    if not any(pt.alive for pt in d.parts):
        return goto(m, "ending_b"), [StopMusic(), PlaySound("victory")]
    if d.hp <= 0:
        m, c = die(m, story.DARK_DEFEAT)
        return m, cmds + c
    return m, cmds


def _chase(d: Dark, mi: Minion, me: Minion, target: Point) -> Minion:
    sx = (target.x > mi.pos.x) - (target.x < mi.pos.x)
    sy = (target.y > mi.pos.y) - (target.y < mi.pos.y)
    for cx, cy in dict.fromkeys([(sx, sy), (sx, 0), (0, sy)]):
        t = Point(mi.pos.x + cx, mi.pos.y + cy)
        if (cx or cy) and t != target and not blocked(d, t, ignore=me):
            return replace(mi, pos=t)
    return mi


def _companion_tick(d: Dark, p: Player) -> tuple[Dark, list[Cmd]]:
    w = d.companion
    if w is None:
        return d, []
    w = replace(w, timer=w.timer + 1, prev=w.pos)
    gap = max(abs(w.pos.x - p.pos.x), abs(w.pos.y - p.pos.y))
    if w.timer % WIZARD_FOLLOW_EVERY == 0 and gap > 1:
        sx = (p.pos.x > w.pos.x) - (p.pos.x < w.pos.x)
        sy = (p.pos.y > w.pos.y) - (p.pos.y < w.pos.y)
        for cx, cy in dict.fromkeys([(sx, sy), (sx, 0), (0, sy)]):
            t = Point(w.pos.x + cx, w.pos.y + cy)
            if (cx or cy) and t != p.pos and not blocked(d, t):
                w = replace(w, pos=t)
                break
    d = replace(d, companion=w)
    if w.timer % COMPANION_EVERY:
        return d, []

    # Nearest enemy within range: minions and boss tiles (not a shielded head)
    best = None
    for mi in d.minions:
        dist = math.dist(mi.pos, w.pos)
        if dist <= COMPANION_RANGE and (best is None or dist < best[0]):
            best = (dist, mi.pos)
    shielded = head_shielded(d)
    for part in d.parts:
        if not part.alive or (part.name == "head" and shielded):
            continue
        cx = min(max(w.pos.x, part.x), part.x + part.w - 1)
        cy = min(max(w.pos.y, part.y), part.y + part.h - 1)
        dist = math.dist((cx, cy), w.pos)
        if dist <= COMPANION_RANGE and (best is None or dist < best[0]):
            best = (dist, Point(cx, cy))
    if best is None:
        return d, []
    target = best[1]
    d, _, cmds = _damage_at(d, target)
    zap = Zap(w.pos.x, w.pos.y, target.x, target.y)
    return replace(d, zaps=d.zaps + (zap,)), cmds + [PlaySound("zap")]
