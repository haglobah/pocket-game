"""Pocket World — A tiny creature explores a wrapping 100x100 tile world."""

from dataclasses import dataclass
from collections import namedtuple
import hashlib

import pyxel

Point = namedtuple("Point", ["x", "y"])


#############
# Constants #
#############

MAP_W = 100
MAP_H = 100
TILE_SIZE = 32
VIEWPORT_W = 24  # tiles visible on screen
VIEWPORT_H = 24
DEBUG_HEIGHT = 60
SCREEN_W = VIEWPORT_W * TILE_SIZE  # 512
SCREEN_H = VIEWPORT_H * TILE_SIZE + DEBUG_HEIGHT

# Tile types
GRASS = 0
TALL_GRASS = 1
FLOWERS = 2
DIRT = 3
WATER = 4
SAND = 5
TREE = 6
ROCK = 7
BUSH = 8

# Tile colors (pyxel palette indices)
TILE_COL = {
    GRASS: 3,
    TALL_GRASS: 11,
    FLOWERS: 3,
    DIRT: 4,
    WATER: 12,
    SAND: 15,
    TREE: 3,
    ROCK: 13,
    BUSH: 3,
}

# Movement speed (frames between steps)
MOVE_DELAY = 4

# Directions
UP = Point(0, -1)
DOWN = Point(0, 1)
LEFT = Point(-1, 0)
RIGHT = Point(1, 0)

# Character sprite colors
COL_BODY = 10       # yellow
COL_EYE = 0         # black
COL_FEET = 4        # brown
COL_BELLY = 9       # orange


###########
# Map Gen #
###########


def _hash_pos(seed: int, x: int, y: int) -> int:
    """Deterministic hash for a tile position given a seed."""
    data = f"{seed}:{x}:{y}".encode()
    return int(hashlib.md5(data).hexdigest(), 16)


def _noise(seed: int, x: int, y: int, scale: float) -> float:
    """Simple value noise with bilinear interpolation."""
    sx = x / scale
    sy = y / scale
    ix, iy = int(sx), int(sy)
    fx, fy = sx - ix, sy - iy
    # Smooth interpolation
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    # Corner values
    v00 = (_hash_pos(seed, ix, iy) % 1000) / 1000.0
    v10 = (_hash_pos(seed, ix + 1, iy) % 1000) / 1000.0
    v01 = (_hash_pos(seed, ix, iy + 1) % 1000) / 1000.0
    v11 = (_hash_pos(seed, ix + 1, iy + 1) % 1000) / 1000.0
    # Bilinear
    top = v00 * (1 - fx) + v10 * fx
    bot = v01 * (1 - fx) + v11 * fx
    return top * (1 - fy) + bot * fy


def generate_map(seed: int) -> tuple[tuple[int, ...], ...]:
    """Generate the 100x100 tile map from a seed. Returns tuple of rows."""
    rows = []
    for y in range(MAP_H):
        row = []
        for x in range(MAP_W):
            elevation = _noise(seed, x, y, 12.0)
            moisture = _noise(seed + 9999, x, y, 15.0)
            detail = _noise(seed + 5555, x, y, 5.0)

            if elevation < 0.30:
                tile = WATER
            elif elevation < 0.36:
                tile = SAND
            elif elevation < 0.75:
                if moisture > 0.65:
                    if detail > 0.6:
                        tile = TREE
                    elif detail > 0.45:
                        tile = BUSH
                    else:
                        tile = TALL_GRASS
                elif moisture > 0.4:
                    if detail > 0.75:
                        tile = FLOWERS
                    elif detail > 0.55:
                        tile = TALL_GRASS
                    else:
                        tile = GRASS
                else:
                    if detail > 0.7:
                        tile = ROCK
                    else:
                        tile = DIRT
            else:
                if detail > 0.5:
                    tile = ROCK
                else:
                    tile = DIRT
            row.append(tile)
        rows.append(tuple(row))
    return tuple(rows)


def is_walkable(tile: int) -> bool:
    return tile not in (WATER, TREE, ROCK)


###########
# Model   #
###########


@dataclass(frozen=True)
class Model:
    player_pos: Point
    facing: Point
    tilemap: tuple[tuple[int, ...], ...]
    seed: int
    move_timer: int  # counts down to 0 for continuous movement
    state: str  # "title" | "play"
    seed_input: str  # text input on title screen
    frame: int  # animation frame counter


##############
# Messages   #
##############


@dataclass(frozen=True)
class Msg:
    pass


@dataclass(frozen=True)
class Tick(Msg):
    pass


@dataclass(frozen=True)
class MoveDir(Msg):
    direction: Point


@dataclass(frozen=True)
class StartGame(Msg):
    seed: int


@dataclass(frozen=True)
class TypeChar(Msg):
    char: str


@dataclass(frozen=True)
class Backspace(Msg):
    pass


@dataclass(frozen=True)
class MapGenerated(Msg):
    tilemap: tuple[tuple[int, ...], ...]
    seed: int


##############
# Commands   #
##############


@dataclass(frozen=True)
class Cmd:
    pass


@dataclass(frozen=True)
class GenerateMap(Cmd):
    seed: int


@dataclass(frozen=True)
class PlayStepSound(Cmd):
    pass


################
# Init/Update  #
################


def init() -> tuple[Model, list[Cmd]]:
    model = Model(
        player_pos=Point(MAP_W // 2, MAP_H // 2),
        facing=DOWN,
        tilemap=(),
        seed=0,
        move_timer=0,
        state="title",
        seed_input="",
        frame=0,
    )
    return model, []


def _wrap(p: Point) -> Point:
    return Point(p.x % MAP_W, p.y % MAP_H)


def _find_spawn(tilemap: tuple[tuple[int, ...], ...]) -> Point:
    """Find a walkable spawn near center."""
    cx, cy = MAP_W // 2, MAP_H // 2
    for r in range(max(MAP_W, MAP_H)):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                p = _wrap(Point(cx + dx, cy + dy))
                if is_walkable(tilemap[p.y][p.x]):
                    return p
    return Point(cx, cy)


def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick():
            new_timer = max(0, model.move_timer - 1)
            new_frame = model.frame + 1
            return Model(
                player_pos=model.player_pos,
                facing=model.facing,
                tilemap=model.tilemap,
                seed=model.seed,
                move_timer=new_timer,
                state=model.state,
                seed_input=model.seed_input,
                frame=new_frame,
            ), []

        case MoveDir(direction=d):
            if model.state != "play":
                return model, []
            if model.move_timer > 0:
                # Still in cooldown, just update facing
                return Model(
                    player_pos=model.player_pos,
                    facing=d,
                    tilemap=model.tilemap,
                    seed=model.seed,
                    move_timer=model.move_timer,
                    state=model.state,
                    seed_input=model.seed_input,
                    frame=model.frame,
                ), []
            new_pos = _wrap(Point(model.player_pos.x + d.x, model.player_pos.y + d.y))
            if not is_walkable(model.tilemap[new_pos.y][new_pos.x]):
                return Model(
                    player_pos=model.player_pos,
                    facing=d,
                    tilemap=model.tilemap,
                    seed=model.seed,
                    move_timer=0,
                    state=model.state,
                    seed_input=model.seed_input,
                    frame=model.frame,
                ), []
            return Model(
                player_pos=new_pos,
                facing=d,
                tilemap=model.tilemap,
                seed=model.seed,
                move_timer=MOVE_DELAY,
                state=model.state,
                seed_input=model.seed_input,
                frame=model.frame,
            ), [PlayStepSound()]

        case StartGame(seed=s):
            return model, [GenerateMap(seed=s)]

        case MapGenerated(tilemap=tm, seed=s):
            spawn = _find_spawn(tm)
            return Model(
                player_pos=spawn,
                facing=DOWN,
                tilemap=tm,
                seed=s,
                move_timer=0,
                state="play",
                seed_input=model.seed_input,
                frame=model.frame,
            ), []

        case TypeChar(char=c):
            if model.state == "title" and len(model.seed_input) < 16:
                return Model(
                    player_pos=model.player_pos,
                    facing=model.facing,
                    tilemap=model.tilemap,
                    seed=model.seed,
                    move_timer=model.move_timer,
                    state=model.state,
                    seed_input=model.seed_input + c,
                    frame=model.frame,
                ), []
            return model, []

        case Backspace():
            if model.state == "title" and model.seed_input:
                return Model(
                    player_pos=model.player_pos,
                    facing=model.facing,
                    tilemap=model.tilemap,
                    seed=model.seed,
                    move_timer=model.move_timer,
                    state=model.state,
                    seed_input=model.seed_input[:-1],
                    frame=model.frame,
                ), []
            return model, []

    return model, []


#######################
# Command interpreter #
#######################


def interpret_cmd(cmd: Cmd) -> list[Msg]:
    match cmd:
        case GenerateMap(seed=s):
            tm = generate_map(s)
            return [MapGenerated(tilemap=tm, seed=s)]
        case PlayStepSound():
            pyxel.play(3, 0)
    return []


########
# View #
########


def draw_tile(sx: int, sy: int, tile: int, frame: int):
    """Draw a tile at screen pixel position (sx, sy) — 32x32."""
    col = TILE_COL[tile]
    pyxel.rect(sx, sy, TILE_SIZE, TILE_SIZE, col)

    match tile:
        case t if t == GRASS:
            # Subtle grass texture — scattered tufts and shade variation
            for pos in [(5, 7), (19, 4), (12, 17), (26, 23), (3, 25),
                        (22, 11), (8, 28), (28, 7), (15, 10), (6, 19)]:
                pyxel.pset(sx + pos[0], sy + pos[1], 11)
            # Tiny grass blade clusters
            for bx, by in [(9, 13), (23, 19), (4, 22)]:
                pyxel.line(sx + bx, sy + by + 3, sx + bx, sy + by, 11)
                pyxel.line(sx + bx + 1, sy + by + 2, sx + bx + 1, sy + by, 3)
        case t if t == TALL_GRASS:
            # Dense grass blades with varied heights and thickness
            for i in range(8):
                bx = sx + 2 + i * 4
                h = 12 + (i % 4) * 2
                by = sy + 30 - h
                pyxel.line(bx, sy + 30, bx, by, 3)
                pyxel.line(bx + 1, sy + 30, bx + 1, by - 1, 3)
                pyxel.line(bx + 2, sy + 30, bx + 2, by + 2, 3)
                # Lighter tips
                pyxel.rect(bx, by - 1, 2, 2, 11)
                # Seed heads on alternating blades
                if i % 2 == 0:
                    pyxel.rect(bx - 1, by - 3, 3, 2, 15)
                    pyxel.pset(bx, by - 4, 15)
        case t if t == FLOWERS:
            # Detailed flowers with petals, stems, and leaves
            # Red flower (5 petals)
            pyxel.line(sx + 7, sy + 12, sx + 7, sy + 24, 3)  # stem
            pyxel.rect(sx + 4, sy + 17, 3, 2, 11)  # leaf
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2)]:
                pyxel.rect(sx + 6 + dx, sy + 10 + dy, 3, 3, 8)
            pyxel.rect(sx + 6, sy + 10, 3, 3, 10)  # center

            # Yellow daisy
            pyxel.line(sx + 21, sy + 14, sx + 21, sy + 26, 3)  # stem
            pyxel.rect(sx + 22, sy + 20, 3, 2, 11)  # leaf
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                pyxel.rect(sx + 20 + dx, sy + 10 + dy, 3, 3, 10)
            pyxel.rect(sx + 20, sy + 10, 3, 3, 9)  # center

            # Small purple flower
            pyxel.line(sx + 14, sy + 20, sx + 14, sy + 28, 3)
            pyxel.rect(sx + 13, sy + 17, 3, 3, 14)
            pyxel.pset(sx + 14, sy + 18, 7)

            # Tiny white wildflowers
            for px_, py_ in [(26, 24), (3, 27), (10, 28)]:
                pyxel.rect(sx + px_, sy + py_, 2, 2, 7)
        case t if t == WATER:
            # Animated water with depth and ripples
            # Depth variation — darker patches
            pyxel.rect(sx + 3, sy + 3, 8, 4, 1)
            pyxel.rect(sx + 18, sy + 14, 8, 4, 1)
            pyxel.rect(sx + 8, sy + 20, 6, 3, 1)
            # Medium depth
            pyxel.rect(sx + 12, sy + 6, 6, 3, 5)
            pyxel.rect(sx + 2, sy + 16, 5, 3, 5)
            # Animated ripple highlights
            offset = (frame // 10) % 32
            for ry, rlen in [(6, 5), (13, 4), (20, 6), (27, 3)]:
                rx = ((offset + ry * 3) % 26) + 3
                pyxel.rect(sx + rx, sy + ry, rlen, 1, 6)
            # Sparkle
            sparkle_x = (frame // 8 + 7) % 28 + 2
            sparkle_y = (frame // 12 + 13) % 28 + 2
            pyxel.pset(sx + sparkle_x, sy + sparkle_y, 7)
        case t if t == SAND:
            # Sandy texture with shells, pebbles, and ripple marks
            # Sand ripple lines
            for ry in [8, 16, 24]:
                pyxel.line(sx + 2, sy + ry, sx + 29, sy + ry, 10)
            # Pebbles
            for px_, py_ in [(7, 5), (22, 18), (5, 22), (18, 4), (27, 27)]:
                pyxel.rect(sx + px_, sy + py_, 2, 2, 10)
            # Shell
            pyxel.rect(sx + 12, sy + 13, 4, 3, 7)
            pyxel.rect(sx + 13, sy + 12, 2, 1, 7)
            pyxel.pset(sx + 13, sy + 14, 6)
            pyxel.line(sx + 12, sy + 15, sx + 15, sy + 15, 10)
            # Darker sand patches
            pyxel.rect(sx + 3, sy + 10, 3, 2, 10)
            pyxel.rect(sx + 24, sy + 8, 3, 2, 10)
        case t if t == TREE:
            # Detailed tree with roots, textured trunk, layered canopy
            # Ground shadow
            pyxel.rect(sx + 6, sy + 28, 20, 3, 11)
            pyxel.rect(sx + 10, sy + 27, 12, 1, 11)
            # Roots
            pyxel.line(sx + 10, sy + 28, sx + 7, sy + 30, 4)
            pyxel.line(sx + 22, sy + 28, sx + 25, sy + 30, 4)
            pyxel.line(sx + 14, sy + 29, sx + 13, sy + 31, 4)
            # Trunk
            pyxel.rect(sx + 12, sy + 17, 8, 12, 4)
            # Bark texture
            pyxel.rect(sx + 14, sy + 18, 3, 10, 2)
            pyxel.pset(sx + 13, sy + 20, 2)
            pyxel.pset(sx + 18, sy + 22, 2)
            pyxel.line(sx + 13, sy + 24, sx + 15, sy + 26, 2)
            # Canopy — back layer (dark green)
            pyxel.circ(sx + 16, sy + 10, 14, 11)
            # Canopy — mid layer (medium green)
            pyxel.circ(sx + 12, sy + 8, 8, 3)
            pyxel.circ(sx + 21, sy + 9, 7, 3)
            pyxel.circ(sx + 16, sy + 12, 7, 3)
            # Canopy — highlights
            pyxel.circ(sx + 14, sy + 6, 5, 11)
            pyxel.circ(sx + 20, sy + 7, 4, 11)
            pyxel.circ(sx + 16, sy + 4, 3, 3)
            # Light spots
            pyxel.rect(sx + 10, sy + 5, 2, 2, 11)
            pyxel.rect(sx + 22, sy + 4, 2, 2, 11)
            pyxel.pset(sx + 16, sy + 2, 3)
        case t if t == ROCK:
            # Large boulder with shading, cracks, and moss
            # Ground shadow
            pyxel.rect(sx + 3, sy + 26, 26, 3, 1)
            # Main body
            pyxel.rect(sx + 4, sy + 8, 24, 18, 13)
            pyxel.rect(sx + 6, sy + 5, 20, 3, 13)
            pyxel.rect(sx + 9, sy + 3, 14, 2, 13)
            # Highlight (top-left face)
            pyxel.rect(sx + 7, sy + 6, 8, 4, 5)
            pyxel.rect(sx + 9, sy + 4, 6, 2, 5)
            pyxel.rect(sx + 8, sy + 10, 4, 3, 5)
            # Shadow (bottom-right)
            pyxel.rect(sx + 18, sy + 20, 8, 5, 1)
            pyxel.rect(sx + 24, sy + 14, 3, 6, 1)
            pyxel.rect(sx + 22, sy + 18, 2, 4, 1)
            # Crack lines
            pyxel.line(sx + 14, sy + 8, sx + 16, sy + 14, 1)
            pyxel.line(sx + 16, sy + 14, sx + 18, sy + 16, 1)
            pyxel.line(sx + 16, sy + 14, sx + 14, sy + 18, 1)
            # Moss patches
            pyxel.rect(sx + 5, sy + 20, 3, 2, 3)
            pyxel.rect(sx + 10, sy + 23, 4, 2, 3)
            pyxel.pset(sx + 7, sy + 22, 11)
        case t if t == BUSH:
            # Detailed bush with layered foliage and berries
            # Ground shadow
            pyxel.rect(sx + 6, sy + 27, 20, 3, 11)
            pyxel.rect(sx + 10, sy + 26, 12, 1, 11)
            # Stem/base
            pyxel.rect(sx + 14, sy + 24, 4, 4, 4)
            # Main foliage — back layer
            pyxel.circ(sx + 16, sy + 16, 12, 11)
            # Mid layer clusters
            pyxel.circ(sx + 10, sy + 14, 7, 3)
            pyxel.circ(sx + 22, sy + 16, 7, 3)
            pyxel.circ(sx + 16, sy + 12, 6, 3)
            # Highlight clusters
            pyxel.circ(sx + 12, sy + 11, 4, 11)
            pyxel.circ(sx + 20, sy + 13, 4, 11)
            pyxel.circ(sx + 16, sy + 10, 3, 3)
            # Leaf detail
            pyxel.rect(sx + 6, sy + 10, 2, 2, 11)
            pyxel.rect(sx + 24, sy + 12, 2, 2, 11)
            # Berries
            pyxel.rect(sx + 11, sy + 18, 3, 3, 8)
            pyxel.pset(sx + 12, sy + 18, 14)
            pyxel.rect(sx + 19, sy + 14, 3, 3, 8)
            pyxel.pset(sx + 20, sy + 14, 14)
            pyxel.rect(sx + 14, sy + 20, 2, 2, 8)
            pyxel.rect(sx + 23, sy + 20, 2, 2, 8)
        case t if t == DIRT:
            # Dirt with texture, pebbles, and cracks
            # Color variation patches
            pyxel.rect(sx + 5, sy + 8, 5, 4, 2)
            pyxel.rect(sx + 18, sy + 4, 6, 3, 2)
            pyxel.rect(sx + 10, sy + 22, 5, 3, 2)
            pyxel.rect(sx + 24, sy + 18, 4, 4, 2)
            # Pebbles
            pyxel.rect(sx + 13, sy + 12, 3, 2, 5)
            pyxel.rect(sx + 22, sy + 10, 2, 2, 5)
            pyxel.rect(sx + 6, sy + 26, 3, 2, 5)
            pyxel.rect(sx + 26, sy + 25, 2, 2, 5)
            # Scattered dots
            for px_, py_ in [(3, 14), (8, 5), (20, 27), (28, 8), (15, 28), (2, 20)]:
                pyxel.pset(sx + px_, sy + py_, 2)
            # Small crack
            pyxel.line(sx + 16, sy + 16, sx + 20, sy + 19, 2)
            pyxel.pset(sx + 20, sy + 20, 2)


def draw_character(sx: int, sy: int, facing: Point, frame: int):
    """Draw a creature sprite at screen pixel position (32x32)."""
    walk_bob = (frame // 6) % 2

    # Shadow on ground
    pyxel.rect(sx + 8, sy + 29, 16, 3, 1)
    pyxel.rect(sx + 12, sy + 28, 8, 1, 1)

    # Body (rounded shape)
    pyxel.rect(sx + 6, sy + 4, 20, 20, COL_BODY)
    pyxel.rect(sx + 8, sy + 2, 16, 24, COL_BODY)
    pyxel.rect(sx + 10, sy + 1, 12, 26, COL_BODY)

    # Belly patch (rounded)
    pyxel.rect(sx + 10, sy + 12, 12, 8, COL_BELLY)
    pyxel.rect(sx + 12, sy + 10, 8, 12, COL_BELLY)
    pyxel.rect(sx + 11, sy + 11, 10, 10, COL_BELLY)

    # Ears
    pyxel.rect(sx + 7, sy, 4, 4, COL_BODY)
    pyxel.rect(sx + 21, sy, 4, 4, COL_BODY)
    # Inner ear
    pyxel.rect(sx + 8, sy + 1, 2, 2, COL_BELLY)
    pyxel.rect(sx + 22, sy + 1, 2, 2, COL_BELLY)

    # Eyes and face based on facing direction
    match facing:
        case Point(0, -1):  # up — show back
            # Back markings
            pyxel.rect(sx + 9, sy + 5, 4, 3, COL_BELLY)
            pyxel.rect(sx + 19, sy + 5, 4, 3, COL_BELLY)
            # Tail
            pyxel.rect(sx + 14, sy + 25, 4, 4, COL_BELLY)
            pyxel.rect(sx + 15, sy + 27, 2, 3, COL_BELLY)
        case Point(0, 1):  # down — face visible
            # Eyes (white sclera + pupil + highlight)
            pyxel.rect(sx + 8, sy + 6, 6, 6, 7)
            pyxel.rect(sx + 18, sy + 6, 6, 6, 7)
            # Pupils
            pyxel.rect(sx + 10, sy + 8, 4, 4, COL_EYE)
            pyxel.rect(sx + 20, sy + 8, 4, 4, COL_EYE)
            # Eye highlights
            pyxel.rect(sx + 11, sy + 8, 2, 2, 7)
            pyxel.rect(sx + 21, sy + 8, 2, 2, 7)
            # Nose
            pyxel.rect(sx + 14, sy + 14, 4, 2, 4)
            # Mouth
            pyxel.line(sx + 13, sy + 18, sx + 16, sy + 19, COL_EYE)
            pyxel.line(sx + 16, sy + 19, sx + 19, sy + 18, COL_EYE)
            # Cheeks (blush)
            pyxel.rect(sx + 6, sy + 13, 3, 2, 8)
            pyxel.rect(sx + 23, sy + 13, 3, 2, 8)
        case Point(-1, 0):  # left
            # Eye on left side
            pyxel.rect(sx + 6, sy + 6, 6, 6, 7)
            pyxel.rect(sx + 6, sy + 8, 4, 4, COL_EYE)
            pyxel.rect(sx + 7, sy + 8, 2, 2, 7)
            # Nose
            pyxel.rect(sx + 4, sy + 13, 3, 2, 4)
            # Mouth
            pyxel.line(sx + 5, sy + 17, sx + 8, sy + 18, COL_EYE)
            # Cheek
            pyxel.rect(sx + 6, sy + 14, 2, 2, 8)
            # Tail
            pyxel.rect(sx + 24, sy + 16, 4, 4, COL_BELLY)
            pyxel.rect(sx + 26, sy + 14, 3, 3, COL_BELLY)
        case Point(1, 0):  # right
            # Eye on right side
            pyxel.rect(sx + 20, sy + 6, 6, 6, 7)
            pyxel.rect(sx + 22, sy + 8, 4, 4, COL_EYE)
            pyxel.rect(sx + 23, sy + 8, 2, 2, 7)
            # Nose
            pyxel.rect(sx + 25, sy + 13, 3, 2, 4)
            # Mouth
            pyxel.line(sx + 24, sy + 17, sx + 27, sy + 18, COL_EYE)
            # Cheek
            pyxel.rect(sx + 24, sy + 14, 2, 2, 8)
            # Tail
            pyxel.rect(sx + 4, sy + 16, 4, 4, COL_BELLY)
            pyxel.rect(sx + 3, sy + 14, 3, 3, COL_BELLY)

    # Arms with swing animation
    if walk_bob:
        pyxel.rect(sx + 4, sy + 12, 3, 6, COL_BODY)
        pyxel.rect(sx + 25, sy + 10, 3, 6, COL_BODY)
        pyxel.rect(sx + 4, sy + 17, 2, 2, COL_BODY)
        pyxel.rect(sx + 26, sy + 15, 2, 2, COL_BODY)
    else:
        pyxel.rect(sx + 4, sy + 10, 3, 6, COL_BODY)
        pyxel.rect(sx + 25, sy + 12, 3, 6, COL_BODY)
        pyxel.rect(sx + 4, sy + 15, 2, 2, COL_BODY)
        pyxel.rect(sx + 26, sy + 17, 2, 2, COL_BODY)

    # Feet with walk animation
    if walk_bob:
        pyxel.rect(sx + 8, sy + 26, 5, 4, COL_FEET)
        pyxel.rect(sx + 19, sy + 24, 5, 4, COL_FEET)
    else:
        pyxel.rect(sx + 8, sy + 24, 5, 4, COL_FEET)
        pyxel.rect(sx + 19, sy + 26, 5, 4, COL_FEET)


def view(model: Model):
    if model.state == "title":
        view_title(model)
    else:
        view_play(model)


def view_title(model: Model):
    pyxel.cls(1)
    # Title
    title = "POCKET WORLD"
    tx = (SCREEN_W - len(title) * pyxel.FONT_WIDTH) // 2
    pyxel.text(tx, 280, title, 7)

    # Seed input
    prompt = "Enter seed (or press ENTER for random):"
    px = (SCREEN_W - len(prompt) * pyxel.FONT_WIDTH) // 2
    pyxel.text(px, 340, prompt, 13)

    input_text = model.seed_input + ("_" if (model.frame // 20) % 2 == 0 else " ")
    ix = (SCREEN_W - len(input_text) * pyxel.FONT_WIDTH) // 2
    pyxel.text(ix, 360, input_text, 7)

    hint = "[ENTER] Start"
    hx = (SCREEN_W - len(hint) * pyxel.FONT_WIDTH) // 2
    pyxel.text(hx, 400, hint, 6)

    # Draw the character as preview
    draw_character(SCREEN_W // 2 - 16, 210, DOWN, model.frame)


def view_play(model: Model):
    pyxel.cls(0)
    px, py = model.player_pos

    # Camera centered on player
    cam_x = px - VIEWPORT_W // 2
    cam_y = py - VIEWPORT_H // 2

    for sy in range(VIEWPORT_H):
        for sx in range(VIEWPORT_W):
            tx = (cam_x + sx) % MAP_W
            ty = (cam_y + sy) % MAP_H
            tile = model.tilemap[ty][tx]
            draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.frame)

    # Draw player at center of screen
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    draw_character(pcx, pcy, model.facing, model.frame)

    # Debug panel below map
    map_bottom = VIEWPORT_H * TILE_SIZE
    pyxel.rect(0, map_bottom, SCREEN_W, DEBUG_HEIGHT, 0)
    dir_name = {UP: "UP", DOWN: "DOWN", LEFT: "LEFT", RIGHT: "RIGHT"}
    tile_name = {
        GRASS: "grass", TALL_GRASS: "tall_grass", FLOWERS: "flowers",
        DIRT: "dirt", WATER: "water", SAND: "sand",
        TREE: "tree", ROCK: "rock", BUSH: "bush",
    }
    standing_on = tile_name.get(model.tilemap[py][px], "?")
    y = map_bottom + 2
    lines = [
        f"seed:{model.seed}  state:{model.state}",
        f"pos:({px},{py})  facing:{dir_name.get(model.facing, '?')}  tile:{standing_on}",
        f"move_timer:{model.move_timer}  frame:{model.frame}",
        f"map:{MAP_W}x{MAP_H}  seed_input:\"{model.seed_input}\"",
    ]
    for line in lines:
        pyxel.text(2, y, line, 7)
        y += pyxel.FONT_HEIGHT + 2


###############
# App (shell) #
###############

# Characters that can be typed for seed input
TYPEABLE = "0123456789abcdefghijklmnopqrstuvwxyz"
PYXEL_KEYS = {c: getattr(pyxel, f"KEY_{c.upper()}") for c in TYPEABLE}


class App:
    def __init__(self):
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="Pocket World",
            fps=60,
            display_scale=1,
        )
        define_sounds()
        self.model, cmds = init()
        self._process_cmds(cmds)
        pyxel.run(self._update, self._draw)

    def _collect_input(self) -> list[Msg]:
        msgs: list[Msg] = []

        if self.model.state == "title":
            # Text input for seed
            for char, key in PYXEL_KEYS.items():
                if pyxel.btnp(key, hold=15, repeat=3):
                    msgs.append(TypeChar(char=char))
            if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=15, repeat=3):
                msgs.append(Backspace())
            if pyxel.btnp(pyxel.KEY_RETURN):
                seed_text = self.model.seed_input.strip()
                if seed_text:
                    seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (2**31)
                else:
                    seed = pyxel.rndi(0, 2**31 - 1)
                msgs.append(StartGame(seed=seed))

        elif self.model.state == "play":
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                msgs.append(MoveDir(direction=UP))
            elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                msgs.append(MoveDir(direction=DOWN))
            elif pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                msgs.append(MoveDir(direction=LEFT))
            elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                msgs.append(MoveDir(direction=RIGHT))

        msgs.append(Tick())
        return msgs

    def _update(self):
        for msg in self._collect_input():
            self.model, cmds = update(self.model, msg)
            self._process_cmds(cmds)

    def _process_cmds(self, cmds: list[Cmd]):
        for cmd in cmds:
            new_msgs = interpret_cmd(cmd)
            for msg in new_msgs:
                self.model, new_cmds = update(self.model, msg)
                self._process_cmds(new_cmds)

    def _draw(self):
        view(self.model)


def define_sounds():
    # Soft footstep sound
    pyxel.sounds[0].set(
        notes="c2",
        tones="n",
        volumes="2",
        effects="f",
        speed=5,
    )


App()
