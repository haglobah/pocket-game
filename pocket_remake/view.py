"""view(): reads the model and draws. Never changes game state.

The minimap keeps a render cache in image bank 1; that is drawing state,
not game state, and it is rebuilt from `model.explored` when needed.
"""

import math

import pyxel

from . import font
from .common import fpos
from .constants import (
    CACTUS,
    CHUNK,
    CLIFF,
    CLIFF_EDGE,
    DARK_SAND,
    DEAD_BUSH,
    DEATH_CONFIRM_DELAY,
    DEEP_WATER,
    FOOD_MAX,
    GREEN_BUSH,
    HEIGHT,
    MAP_H,
    MAP_W,
    O2_MAX,
    PALM,
    PORTAL,
    RED_BUSH,
    REWIND_FRAMES,
    ROCK,
    SWIMMABLE,
    TILE,
    WATER,
    WATER_MAX,
    WIDTH,
    WIZARD_LISTEN_RANGE,
    WRECK,
    YELLOW_BUSH,
)
from .dark import ARENA_H, ARENA_W, arena_tile, head_shielded
from .mapgen import chebyshev, tile_at, wrap_delta
from .model import Model
from .sprites import SLOT
from .story import DIALOGUE

CX = WIDTH // 2 - TILE // 2  # screen position of the player's tile
CY = HEIGHT // 2 - TILE // 2
HUD_Y = HEIGHT - 64


def view(m: Model) -> None:
    match m.state:
        case "title":
            _title(m)
        case "play":
            _play(m)
        case "dead":
            _dead(m)
        case "rewind":
            _rewind(m)
        case "dark_play":
            _dark(m)
        case "ending_b":
            _ending(m)


# --- helpers -------------------------------------------------------------


def spr(
    name: str, x: float, y: float, flip: bool = False, h: int = TILE, key=0
) -> None:
    u, v = SLOT[name]
    pyxel.blt(int(x), int(y), 0, u, v, -TILE if flip else TILE, h, key)


def white(on: bool) -> None:
    if on:
        for c in range(1, 16):
            pyxel.pal(c, 7)
    else:
        pyxel.pal()


def stars(m: Model, count: int = 90, col: int = 7) -> None:
    for i in range(count):
        x = (i * 7919) % WIDTH
        y = (i * 104729) % HEIGHT
        if (m.frame // 20 + i) % 7:
            pyxel.pset(x, y, col if i % 3 else 6)


def panel(x: int, y: int, w: int, h: int, fill: int, edge: int) -> None:
    pyxel.rect(x + 2, y, w - 4, h, edge)
    pyxel.rect(x, y + 2, w, h - 4, edge)
    pyxel.rect(x + 2, y + 2, w - 4, h - 4, fill)


def vignette(col: int, alpha: float, size: int = 28) -> None:
    pyxel.dither(alpha)
    pyxel.rect(0, 0, WIDTH, size, col)
    pyxel.rect(0, HEIGHT - size, WIDTH, size, col)
    pyxel.rect(0, 0, size, HEIGHT, col)
    pyxel.rect(WIDTH - size, 0, size, HEIGHT, col)
    pyxel.dither(1.0)


def blink(m: Model, period: int = 30) -> bool:
    return (m.frame // period) % 2 == 0


# --- title ---------------------------------------------------------------


def _title(m: Model) -> None:
    pyxel.cls(1)
    stars(m)
    # The pocket world below, and a ship falling towards it
    pyxel.circ(256, 760, 380, 4)
    pyxel.circ(256, 770, 372, 9)
    pyxel.circ(256, 780, 360, 15)
    for i in range(6):
        pyxel.elli(60 + i * 70, 418 + (i % 2) * 14, 60, 10, 9)
    t = m.frame % 300
    if t < 120:
        sx, sy = 40 + t * 3.2, 40 + t * 2.4
        for k in range(10):
            pyxel.pset(int(sx - k * 3.2), int(sy - k * 2.4), 10 if k < 4 else 9)
        pyxel.circ(sx, sy, 2, 7)

    font.center(96, "POCKET WORLD", 10, scale=6, under=2)
    font.center(150, "a stranger falls. the world remembers.", 6)

    font.center(250, "Enter seed (or press ENTER for random):", 7)
    w = 16 * 8 + 24
    x = (WIDTH - w) // 2
    panel(x, 274, w, 28, 0, 13)
    shown = m.seed_text + ("_" if blink(m, 20) else " ")
    font.text(x + 12, 282, shown, 10)

    font.center(468, "WASD move  C sprint  Q drink  E eat  B gills  M map", 15, under=4)


# --- overworld -----------------------------------------------------------

MINIMAP_COLOR = {
    DARK_SAND: 9,
    CLIFF: 4,
    CLIFF_EDGE: 2,
    PALM: 11,
    CACTUS: 3,
    ROCK: 13,
    WATER: 12,
    DEEP_WATER: 5,
    GREEN_BUSH: 11,
    RED_BUSH: 8,
    YELLOW_BUSH: 10,
    PORTAL: 14,
    WRECK: 7,
}

OBJECT_SPRITE = {
    DEAD_BUSH: "dead_bush",
    ROCK: "rock",
    GREEN_BUSH: "bush_green",
    RED_BUSH: "bush_red",
    YELLOW_BUSH: "bush_yellow",
}


def _base_sprite(t: int, x: int, y: int, frame: int) -> str:
    if t == DARK_SAND:
        return "dark_sand"
    if t == CLIFF:
        return "cliff"
    if t == CLIFF_EDGE:
        return "cliff_edge"
    if t == WATER:
        return "water_a" if (frame // 40 + x + y) % 2 else "water_b"
    if t == DEEP_WATER:
        return "deep_water"
    h = ((x * 73856093) ^ (y * 19349663)) % 10
    return "sand_ripple" if h == 0 else "sand_b" if h < 4 else "sand_a"


def _object_sprite(m: Model, t: int, x: int, y: int) -> str | None:
    if t == PALM:
        return "palm_empty" if (x % MAP_W, y % MAP_H) in m.eaten else "palm"
    if t == CACTUS:
        return "cactus_empty" if (x % MAP_W, y % MAP_H) in m.eaten else "cactus"
    if t == PORTAL:
        return "portal_a" if (m.frame // 10) % 2 else "portal_b"
    return OBJECT_SPRITE.get(t)


def _to_screen(cam_px: tuple[int, int], x: float, y: float, cam: tuple[float, float]):
    """World tile coords -> screen pixels, the wrapped short way."""
    dx = wrap_delta(x - cam[0], MAP_W)
    dy = wrap_delta(y - cam[1], MAP_H)
    return CX + round(dx * TILE), CY + round(dy * TILE)


def _play(m: Model) -> None:
    world = m.world
    p = m.player
    cam = fpos(p)
    cam_px = (round(cam[0] * TILE), round(cam[1] * TILE))
    ox, oy = math.floor(cam[0]), math.floor(cam[1])
    pyxel.cls(15)

    for j in range(-17, 18):
        for i in range(-17, 18):
            wx, wy = ox + i, oy + j
            sx = wx * TILE - cam_px[0] + CX
            sy = wy * TILE - cam_px[1] + CY
            if sx <= -TILE or sy <= -TILE or sx >= WIDTH or sy >= HEIGHT:
                continue
            t = tile_at(world, wx, wy)
            spr(_base_sprite(t, wx, wy, m.frame), sx, sy, key=None)
            obj = _object_sprite(m, t, wx, wy)
            if obj:
                spr(obj, sx, sy)

    portal_x, portal_y = _to_screen(cam_px, *world.portal, cam)
    if -64 < portal_x < WIDTH + 64 and -64 < portal_y < HEIGHT + 64:
        for k in range(3):
            r = 10 + ((m.frame // 2 + k * 8) % 24)
            pyxel.circb(portal_x + 8, portal_y + 8, r, 2 if k % 2 else 14)

    wx, wy = _to_screen(cam_px, world.spawn.x - 1, world.spawn.y - 2, cam)
    if -64 < wx < WIDTH + 16 and -64 < wy < HEIGHT + 16:
        _wreck(wx, wy, m.frame)

    if m.wizard is not None:
        _wizard_sprite(m, m.wizard, *_to_screen(cam_px, *m.wizard.pos, cam), cam)
    for b in m.bolts:
        bx, by = _to_screen(cam_px, b.x, b.y, cam)
        _bolt(bx + 8, by + 8, b.vx, b.vy, m.frame)

    wet = tile_at(world, *p.pos) in SWIMMABLE and p.move_cd == 0
    _karl(m, p, CX, CY, wet)
    if m.state_timer < 40:
        r = (40 - m.state_timer) * 2
        pyxel.circb(CX + 8, CY + 8, r, 6)
        pyxel.circb(CX + 8, CY + 8, r // 2, 7)

    if p.poison > 0:
        vignette(2, 0.35 + 0.15 * math.sin(m.frame / 6))
    if p.o2 < O2_MAX // 4:
        vignette(1, 0.5 - p.o2 / O2_MAX)
    if p.water < 15 * 60 or p.food < 15 * 60:
        vignette(8, 0.25 if blink(m, 20) else 0.1, 16)

    if m.wizard is not None:
        _wizard_talk(m, cam_px, cam)
    if m.thought is not None:
        _thought(m)
    _hud(m)
    _minimap(m)


def _wreck(x: int, y: int, frame: int) -> None:
    pyxel.elli(x + 2, y + 22, 46, 10, 4)
    pyxel.tri(x + 4, y + 10, x - 2, y - 2, x + 14, y + 8, 5)  # torn fin
    pyxel.elli(x, y + 6, 46, 22, 5)
    pyxel.elli(x + 1, y + 6, 44, 18, 13)
    pyxel.rect(x + 6, y + 10, 32, 2, 7)
    pyxel.circ(x + 34, y + 16, 5, 1)
    pyxel.circ(x + 34, y + 16, 3, 6)
    pyxel.line(x + 10, y + 20, x + 22, y + 14, 0)
    pyxel.pset(x + 16, y + 22, 4)
    # The checkpoint machine still blinks
    pyxel.rect(x + 18, y + 18, 4, 3, 12 if (frame // 20) % 3 else 7)
    for k in range(3):
        t = (frame + k * 40) % 120
        px = x + 10 + math.sin(t / 9) * 3
        pyxel.circ(px, y + 4 - t / 4, 2 + t / 40, 13 if t < 70 else 5)


def _karl(m: Model, p, x: int, y: int, wet: bool) -> None:
    moving = p.move_cd > 0
    frame = "b" if moving and (m.frame // 6) % 2 else "a"
    fx, fy = p.facing
    if fx:
        name, flip = f"karl_side_{frame}", fx < 0
    elif fy < 0:
        name, flip = f"karl_up_{frame}", False
    else:
        name, flip = f"karl_down_{frame}", False
    if wet:
        bob = (m.frame // 20) % 2
        spr(name, x, y + 4 + bob, flip, h=10)
        pyxel.line(x, y + 14, x + 15, y + 14, 7)
        pyxel.line(x + 2 + bob * 2, y + 15, x + 12, y + 15, 6)
        if p.breath == "gills" and (m.frame // 15) % 4 == 0:
            pyxel.circb(x + 12, y - 2 - (m.frame // 15) % 8, 2, 7)
    else:
        pyxel.elli(x + 3, y + 13, 10, 4, 4)
        spr(name, x, y, flip)
        if p.breath == "gills":
            pyxel.pset(x + 3, y + 5, 12)
            pyxel.pset(x + 12, y + 5, 12)


def _wizard_sprite(m: Model, w, x: int, y: int, cam) -> None:
    flip = wrap_delta(cam[0] - w.pos.x, MAP_W) < 0 if m.state == "play" else False
    pyxel.elli(x + 3, y + 13, 10, 4, 4 if m.state == "play" else 0)
    spr("wizard_a" if (m.frame // 30) % 2 else "wizard_b", x, y, flip)
    if w.mode == "attack":
        pyxel.circb(x + (1 if flip else 15), y + 1, 3 + (m.frame // 4) % 2, 12)
    elif w.mode == "follow":
        pyxel.pset(x + (1 if flip else 15), y + 1, 7 if blink(m, 10) else 12)


def _bolt(x: int, y: int, vx: float, vy: float, frame: int) -> None:
    d = math.hypot(vx, vy) or 1
    ux, uy = -vx / d, -vy / d
    px, py = x, y
    for k in range(1, 4):
        jx = ((frame + k) % 3 - 1) * 3
        nx, ny = x + ux * k * 6 + jx * -uy, y + uy * k * 6 + jx * ux
        pyxel.line(px, py, nx, ny, 12)
        px, py = nx, ny
    pyxel.circ(x, y, 3, 12)
    pyxel.circ(x, y, 1, 7)


def _bubble_box(lines: list[str], anchor_x: int, top: int, fill: int, edge: int):
    w = max(len(s) for s in lines) * 8 + 16
    h = len(lines) * 14 + 10
    x = max(6, min(WIDTH - w - 6, anchor_x - w // 2))
    y = max(6, top - h)
    panel(x, y, w, h, fill, edge)
    return x, y, w, h


def _thought(m: Model) -> None:
    t = m.thought
    shown = t.text[: t.age // 3]
    lines = font.wrap(t.text, 34)
    # type the text in, keeping the wrapped layout stable
    typed, left = [], len(shown)
    for line in lines:
        typed.append(line[: max(0, left)])
        left -= len(line) + 1
    x, y, _, _ = _bubble_box(lines, CX + 8, CY - 30, 7, 1)
    for k, line in enumerate(typed):
        font.text(x + 8, y + 6 + k * 14, line, 1)
    pyxel.circ(CX + 12, CY - 8, 3, 1)
    pyxel.circ(CX + 12, CY - 8, 2, 7)
    pyxel.circ(CX + 16, CY - 18, 5, 1)
    pyxel.circ(CX + 16, CY - 18, 4, 7)


def _wizard_talk(m: Model, cam_px, cam) -> None:
    w = m.wizard
    near = chebyshev(w.pos, m.player.pos)
    if w.mode == "talk":
        if near > WIZARD_LISTEN_RANGE:
            return
        text, options = DIALOGUE[w.node]
        lines = font.wrap(text, 56)
        h = 34 + len(lines) * 14 + 2 * 16
        y = HUD_Y - h - 8
        panel(12, y, WIDTH - 24, h, 1, 6)
        font.text(24, y + 8, "THE WISE MAN", 10)
        for k, line in enumerate(lines):
            font.text(24, y + 26 + k * 14, line, 7)
        oy = y + 30 + len(lines) * 14
        for k, (label, _) in enumerate(options):
            font.text(24, oy + k * 16, f"[{k + 1}]", 10)
            font.text(56, oy + k * 16, label, 15)
        return
    if w.line and near <= 18:
        x, y = _to_screen(cam_px, *w.pos, cam)
        lines = font.wrap(w.line, 30)
        bx, by, _, bh = _bubble_box(lines, x + 8, y - 6, 2, 14)
        for k, line in enumerate(lines):
            font.text(bx + 8, by + 6 + k * 14, line, 7)
        if by + bh < y:
            pyxel.tri(x + 4, by + bh, x + 12, by + bh, x + 8, y - 2, 14)


def _bar(
    x: int, y: int, label: str, value: int, maximum: int, col: int, alert: bool, m
):
    font.shadow(x, y - 2, label, 7)
    bx = x + 112
    pyxel.rect(bx - 1, y - 1, 162, 10, 0)
    fill = max(0, min(160, int(160 * value / maximum)))
    pyxel.rect(bx, y, fill, 8, col)
    if alert and blink(m, 10):
        pyxel.rectb(bx - 2, y - 2, 164, 12, 8)


def _hud(m: Model) -> None:
    p = m.player
    pyxel.dither(0.55)
    pyxel.rect(0, HUD_Y, WIDTH, 64, 0)
    pyxel.dither(1.0)
    wet = tile_at(m.world, *p.pos) in SWIMMABLE
    rows = []
    if p.breath == "gills" or p.o2 < O2_MAX or wet or p.poison:
        col = 2 if p.poison else 6
        rows.append((f"O2 [{p.breath.upper()}]", p.o2, O2_MAX, col, p.o2 < O2_MAX // 4))
    rows.append(("Water [Q]", p.water, WATER_MAX, 12, p.water < 15 * 60))
    rows.append(("Food [E]", p.food, FOOD_MAX, 9, p.food < 15 * 60))
    for k, row in enumerate(rows):
        _bar(12, HUD_Y + 10 + k * 18, *row, m)
    font.shadow(
        WIDTH - 12 - font.width(f"CYCLE {m.cycle}"), HUD_Y + 8, f"CYCLE {m.cycle}", 10
    )
    if p.poison:
        msg = "POISONED"
        font.shadow(
            WIDTH - 12 - font.width(msg), HUD_Y + 26, msg, 14 if blink(m, 8) else 2
        )
    elif wet and p.breath == "lungs":
        msg = "[B] gills"
        font.shadow(WIDTH - 12 - font.width(msg), HUD_Y + 26, msg, 6)
    elif wet:
        msg = "[SPACE] breathe"
        font.shadow(WIDTH - 12 - font.width(msg), HUD_Y + 26, msg, 6)
    elif p.breath == "gills":
        msg = "[B] lungs"
        font.shadow(WIDTH - 12 - font.width(msg), HUD_Y + 26, msg, 6)


_mini = {"seed": None, "count": -1, "drawn": set()}
MINI = 128  # panel size; 1 px = 2 tiles


def _mini_px(m: Model, x: int, y: int) -> tuple[int, int]:
    s = m.world.spawn
    return (
        (int(wrap_delta(x - s.x, MAP_W)) + 256) // 2,
        (int(wrap_delta(y - s.y, MAP_H)) + 256) // 2,
    )


def _refresh_minimap(m: Model) -> None:
    img = pyxel.images[1]
    if _mini["seed"] != m.seed:
        img.cls(0)
        _mini.update(seed=m.seed, count=-1, drawn=set())
    if _mini["count"] == len(m.explored):
        return
    for cx, cy in m.explored - _mini["drawn"]:
        for sy in range(0, CHUNK, 2):
            for sx in range(0, CHUNK, 2):
                x, y = cx * CHUNK + sx, cy * CHUNK + sy
                u, v = _mini_px(m, x, y)
                if 0 <= u < 256 and 0 <= v < 256:
                    img.pset(u, v, MINIMAP_COLOR.get(tile_at(m.world, x, y), 15))
        _mini["drawn"].add((cx, cy))
    _mini["count"] = len(m.explored)


def _minimap(m: Model) -> None:
    label = "[M] Map"
    x0 = WIDTH - MINI - 12
    if not m.show_map:
        font.shadow(WIDTH - 12 - font.width(label), 10, label, 7)
        return
    _refresh_minimap(m)
    pyxel.rect(x0 - 3, 7, MINI + 6, MINI + 6, 1)
    pyxel.rect(x0, 10, MINI, MINI, 0)
    pcx, pcy = _mini_px(m, *m.player.pos)
    ox, oy = x0 + MINI // 2 - pcx, 10 + MINI // 2 - pcy
    pyxel.clip(x0, 10, MINI, MINI)
    pyxel.blt(ox, oy, 1, 0, 0, 256, 256)
    sx, sy = _mini_px(m, *m.world.spawn)
    pyxel.rect(ox + sx - 1, oy + sy - 1, 3, 3, 12)
    if "wormhole" in m.seen:
        px, py = _mini_px(m, *m.world.portal)
        pyxel.circb(ox + px, oy + py, 2 + (m.frame // 8) % 3, 14)
    if m.wizard is not None:
        wx, wy = _mini_px(m, *m.wizard.pos)
        pyxel.rect(ox + wx, oy + wy, 2, 2, 2)
    pyxel.clip()
    if blink(m, 8):
        pyxel.rect(x0 + MINI // 2 - 1, 10 + MINI // 2 - 1, 3, 3, 7)
    font.shadow(x0, MINI + 16, label, 7)


# --- dark world ----------------------------------------------------------


def _dark(m: Model) -> None:
    d = m.dark
    p = m.player
    cam = fpos(p)
    cam_px = (round(cam[0] * TILE), round(cam[1] * TILE))
    pyxel.cls(0)
    stars(m, 60, 2)

    def at(x: float, y: float) -> tuple[int, int]:
        return CX + round(x * TILE) - cam_px[0], CY + round(y * TILE) - cam_px[1]

    ox, oy = math.floor(cam[0]), math.floor(cam[1])
    for j in range(-17, 18):
        for i in range(-17, 18):
            x, y = ox + i, oy + j
            if 0 <= x < ARENA_W and 0 <= y < ARENA_H:
                t = arena_tile(x, y)
                spr("dark_wall" if t != 14 else "dark_floor", *at(x, y), key=None)

    shielded = head_shielded(d)
    for part in d.parts:
        x, y = at(part.x, part.y)
        _boss_part(m, part, x, y, part.w * TILE, part.h * TILE, shielded)

    for mi in d.minions:
        x, y = at(*fpos_minion(mi))
        white(mi.flash > 0 and m.frame % 4 < 2)
        spr(mi.kind, x, y, flip=(m.frame // 20) % 2 == 0)
        white(False)

    if d.companion is not None:
        w = d.companion
        _wizard_sprite(m, w, *at(w.pos.x, w.pos.y), cam)
    for z in d.zaps:
        x0, y0 = at(z.x0, z.y0)
        x1, y1 = at(z.x1, z.y1)
        mx, my = (x0 + x1) / 2 + (z.age % 3 - 1) * 6, (y0 + y1) / 2 - 6
        pyxel.line(x0 + 15, y0 + 1, mx + 8, my + 8, 12)
        pyxel.line(mx + 8, my + 8, x1 + 8, y1 + 8, 7)

    for s in d.shots:
        x, y = at(s.x, s.y)
        pyxel.circ(x + 8, y + 8, 5, 8)
        pyxel.circ(x + 8, y + 8, 3, 14)
        pyxel.circ(x + 8, y + 8, 1, 7)

    if not (d.iframes and (m.frame // 4) % 2):
        _karl(m, p, CX, CY, False)
    if d.punch_anim:
        reach = 1 + (8 - d.punch_anim) / 8
        fx, fy = CX + p.facing.x * reach * TILE, CY + p.facing.y * reach * TILE
        pyxel.circ(fx + 8, fy + 8, 5, 7)
        pyxel.circb(fx + 8, fy + 8, 7 + (8 - d.punch_anim), 10)
    if d.iframes > 40:
        vignette(8, 0.4)

    # HUD
    alive = sum(1 for pt in d.parts if pt.alive)
    font.shadow(12, 10, f"Boss: {alive}/{len(d.parts)} parts", 14)
    font.shadow(12, 28, f"Minions: {len(d.minions)}", 13)
    pyxel.dither(0.55)
    pyxel.rect(0, HEIGHT - 32, WIDTH, 32, 0)
    pyxel.dither(1.0)
    for k in range(5):
        col = 8 if k < d.hp else 1
        _heart(14 + k * 22, HEIGHT - 24, col)
    font.shadow(132, HEIGHT - 22, f"HP:{d.hp}/5 [F] Punch [WASD/Arrows] Move", 7)


def fpos_minion(mi) -> tuple[float, float]:
    return float(mi.pos.x), float(mi.pos.y)


def _heart(x: int, y: int, col: int) -> None:
    pyxel.circ(x + 4, y + 4, 4, col)
    pyxel.circ(x + 12, y + 4, 4, col)
    pyxel.tri(x, y + 5, x + 16, y + 5, x + 8, y + 14, col)


def _boss_part(m: Model, part, x: int, y: int, w: int, h: int, shielded: bool) -> None:
    f = m.frame
    if not part.alive:
        for k in range(5):
            rx = x + (k * 37) % max(1, w - 12)
            ry = y + h - 12 - (k * 13) % max(1, h // 2)
            pyxel.elli(rx, ry, 14, 8, 5 if k % 2 else 2)
        return
    white(part.flash > 0 and f % 4 < 2)
    if part.name == "wings":
        flap = round(math.sin(f / 18) * 8)
        cxm = x + w // 2
        for side in (-1, 1):
            tip = cxm + side * (w // 2)
            pyxel.tri(cxm, y + h, tip, y + flap, tip, y + h - 8, 2)
            pyxel.tri(
                cxm, y + h, tip, y + flap, cxm + side * w // 4, y + 8 + flap // 2, 2
            )
            for k in range(3):
                pyxel.line(cxm, y + h, tip - side * k * 20, y + flap + k * 10, 1)
            pyxel.line(cxm + side * w // 4, y + 8 + flap // 2, tip, y + flap, 14)
    elif part.name in ("left_arm", "right_arm"):
        sway = round(math.sin(f / 14 + (0 if part.name == "left_arm" else 3)) * 4)
        pyxel.rect(x + 12, y, w - 24, h - 20, 5)
        pyxel.rect(x + 14, y + 4, 4, h - 28, 13)
        pyxel.rect(x + 6 + sway, y + h - 24, w - 12, 10, 5)
        pyxel.tri(
            x + 4 + sway, y + h - 14, x + 18 + sway, y + h - 14, x + 8 + sway, y + h, 13
        )
        pyxel.tri(
            x + w - 18 + sway,
            y + h - 14,
            x + w - 4 + sway,
            y + h - 14,
            x + w - 8 + sway,
            y + h,
            13,
        )
    else:
        cxm, cym = x + w // 2, y + h // 2
        pyxel.circ(cxm, cym, w // 2 - 2, 2)
        pyxel.circb(cxm, cym, w // 2 - 2, 14)
        pyxel.circ(cxm, cym - 4, 14, 0)
        pyxel.circ(cxm, cym - 4, 10, 8 if m.dark.fire_cd > 20 else 14)
        pdx, pdy = m.player.pos.x - (part.x + 2), m.player.pos.y - (part.y + 2)
        dd = math.hypot(pdx, pdy) or 1
        pyxel.circ(cxm + pdx / dd * 5, cym - 4 + pdy / dd * 5, 4, 7)
        mouth = 14 if m.dark.fire_cd < 20 and f % 4 < 2 else 1
        pyxel.rect(cxm - 12, cym + 16, 24, 4, mouth)
        if shielded:
            r = w // 2 + 4 + (f // 6) % 3
            pyxel.dither(0.6)
            pyxel.circb(cxm, cym, r, 6)
            pyxel.circb(cxm, cym, r - 2, 12)
            pyxel.dither(1.0)
    white(False)
    # health pips
    for k in range(part.max_hp):
        pyxel.rect(x + k * 6, y - 6, 4, 3, 8 if k < part.hp else 1)


# --- screens -------------------------------------------------------------


def _dead(m: Model) -> None:
    pyxel.cls(0)
    for k in range(0, HEIGHT, 8):
        pyxel.line(0, k, WIDTH, k, 1 if k % 16 else 0)
    font.center(80, f"Cycle {m.cycle} -- You died", 8, scale=3, under=2)
    font.center(132, f"Seed: {m.seed_text}", 13)
    for k, line in enumerate(font.wrap(f"Reason: {m.death_reason}", 58)):
        font.center(160 + k * 14, line, 7)
    y = 216
    if m.learned:
        font.center(y, "In this cycle, you learned:", 10)
        for k, skill in enumerate(m.learned):
            font.center(y + 24 + k * 16, f"- {skill}", 15)
    else:
        font.center(y, "You didn't learn anything this cycle.", 13)
    if m.state_timer >= DEATH_CONFIRM_DELAY and blink(m, 30):
        font.center(452, "[ENTER] Continue", 7)


def _rewind(m: Model) -> None:
    pyxel.cls(1)
    t = min(1.0, m.state_timer / REWIND_FRAMES)
    cx, cy = WIDTH // 2, 220
    for k in range(12):
        a = -k * math.pi / 6 - m.state_timer / 20
        r0, r1 = 110, 130 + (k % 3) * 8
        pyxel.line(
            cx + math.cos(a) * r0,
            cy + math.sin(a) * r0,
            cx + math.cos(a) * r1,
            cy + math.sin(a) * r1,
            5,
        )
    _hourglass(cx, cy, t, m.frame)
    font.center(340, "Rewinding" + "." * (1 + (m.state_timer // 20) % 3), 7)
    font.center(366, f"Cycle {m.cycle + 1}", 10, scale=3, under=2)


def _hourglass(cx: int, cy: int, t: float, frame: int) -> None:
    """Sand flows back up: the bottom empties into the top."""
    top, bottom = t, 1 - t
    if top > 0:
        pyxel.tri(
            cx - 30 * top,
            cy - 4 - 48 * top,
            cx + 30 * top,
            cy - 4 - 48 * top,
            cx,
            cy - 4,
            10,
        )
        pyxel.tri(
            cx - 30 * top,
            cy - 4 - 48 * top,
            cx + 30 * top,
            cy - 4 - 48 * top,
            cx,
            cy - 4 - 48 * top - 4,
            10,
        )
    if bottom > 0:
        pyxel.tri(
            cx - 30 * bottom,
            cy + 52,
            cx + 30 * bottom,
            cy + 52,
            cx,
            cy + 52 - 44 * bottom,
            10,
        )
    if 0 < t < 1:
        for k in range(0, 48, 4):
            if (k + frame) % 8 < 4:
                pyxel.pset(cx, cy + 50 - k, 15)
    pyxel.line(cx - 32, cy - 54, cx - 3, cy - 2, 6)
    pyxel.line(cx + 32, cy - 54, cx + 3, cy - 2, 6)
    pyxel.line(cx - 3, cy + 2, cx - 32, cy + 54, 6)
    pyxel.line(cx + 3, cy + 2, cx + 32, cy + 54, 6)
    pyxel.rect(cx - 40, cy - 62, 80, 8, 4)
    pyxel.rect(cx - 40, cy + 54, 80, 8, 4)
    pyxel.rect(cx - 38, cy - 54, 4, 108, 4)
    pyxel.rect(cx + 34, cy - 54, 4, 108, 4)


def _ending(m: Model) -> None:
    pyxel.cls(1)
    stars(m, 140)
    pyxel.circ(256, 650, 300, 3)
    pyxel.circ(256, 660, 290, 11)
    for k in range(5):
        pyxel.elli(80 + k * 80, 380 + (k % 2) * 16, 50, 12, 3)
    font.center(70, "YOU SAVED THE", 10, scale=4, under=2)
    font.center(104, "POCKET WORLD", 10, scale=4, under=2)
    font.center(170, "The dark pocket world has been defeated.", 7)
    font.center(190, "The stolen land returns to its rightful place.", 7)
    font.center(210, "Peace is restored.", 7)
    font.center(250, "-- ENDING B --", 14)
    if m.state_timer >= DEATH_CONFIRM_DELAY and blink(m, 30):
        font.center(460, "[ENTER] Return to Title", 7, under=1)
