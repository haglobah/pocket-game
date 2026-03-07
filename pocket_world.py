"""Pocket World — A tiny creature explores a wrapping 100x100 tile world."""

from dataclasses import dataclass, replace
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
def is_walkable(tile: int) -> bool:
    return tile in (GRASS, TALL_GRASS, BUSH, FLOWERS, DIRT, SAND)

def is_swimmable(tile: int) -> bool:
    return tile is WATER


# Movement speed (frames between steps)
MOVE_DELAY_WATER = 12
MOVE_DELAY_LAND = 8
MOVE_DELAY_RUNNING = 4

# O2 system
O2_MAX = 40 * 60  # 40 seconds at 60fps
O2_BREATHE_REFILL = 20 * 60  # 20 seconds refill per key press
O2_AUTO_REFILL_RATE = 4  # frames of O2 restored per frame when auto-breathing

# Breathing modes
LUNGS = "lungs"
GILLS = "gills"

# Directions
UP = Point(0, -1)
DOWN = Point(0, 1)
LEFT = Point(-1, 0)
RIGHT = Point(1, 0)

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
    o2: int  # O2 in frames remaining (max O2_MAX)
    breathing_mode: str  # LUNGS or GILLS


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


@dataclass(frozen=True)
class Breathe(Msg):
    pass


@dataclass(frozen=True)
class ToggleBreathingMode(Msg):
    pass


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

@dataclass(frozen=True)
class PlaySwimSound(Cmd):
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
        o2=O2_MAX,
        breathing_mode=LUNGS,
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
                if is_swimmable(tilemap[p.y][p.x]):
                    return p
    return Point(cx, cy)


def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick():
            new_o2 = model.o2
            if model.state == "play" and model.tilemap:
                underwater = model.tilemap[model.player_pos.y][model.player_pos.x] == WATER
                can_auto_breathe = (model.breathing_mode == LUNGS and not underwater)
                if can_auto_breathe:
                    new_o2 = min(O2_MAX, new_o2 + O2_AUTO_REFILL_RATE)
                else:
                    new_o2 = max(0, new_o2 - 1)
            return replace(
                model,
                move_timer=max(0, model.move_timer - 1),
                frame=model.frame + 1,
                o2=new_o2,
            ), []

        case MoveDir(direction=d):
            if model.state != "play":
                return model, []
            if model.move_timer > 0:
                # Still in cooldown, just update facing
                return replace(model, facing=d), []
            new_pos = _wrap(Point(model.player_pos.x + d.x, model.player_pos.y + d.y))
            if is_walkable(model.tilemap[new_pos.y][new_pos.x]):
                return replace(
                    model, player_pos=new_pos, facing=d, move_timer=MOVE_DELAY_LAND,
                ), [PlayStepSound()]
            if is_swimmable(model.tilemap[new_pos.y][new_pos.x]):
                return replace(
                    model, player_pos=new_pos, facing=d, move_timer=MOVE_DELAY_WATER,
                ), [PlaySwimSound()]
            return replace(model, facing=d, move_timer=0), []

        case StartGame(seed=s):
            return model, [GenerateMap(seed=s)]

        case MapGenerated(tilemap=tm, seed=s):
            spawn = _find_spawn(tm)
            return replace(
                model,
                player_pos=spawn,
                facing=DOWN,
                tilemap=tm,
                seed=s,
                move_timer=0,
                state="play",
            ), []

        case TypeChar(char=c):
            if model.state == "title" and len(model.seed_input) < 16:
                return replace(model, seed_input=model.seed_input + c), []
            return model, []

        case Backspace():
            if model.state == "title" and model.seed_input:
                return replace(model, seed_input=model.seed_input[:-1]), []
            return model, []

        case Breathe():
            if model.state != "play" or not model.tilemap:
                return model, []
            underwater = model.tilemap[model.player_pos.y][model.player_pos.x] == WATER
            if model.breathing_mode == GILLS and underwater:
                new_o2 = min(O2_MAX, model.o2 + O2_BREATHE_REFILL)
                return replace(model, o2=new_o2), []
            return model, []

        case ToggleBreathingMode():
            new_mode = GILLS if model.breathing_mode == LUNGS else LUNGS
            return replace(model, breathing_mode=new_mode), []

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
        case PlaySwimSound():
            pyxel.play(3, 0)
    return []


########
# View #
########


def draw_tile(sx: int, sy: int, tile: int, frame: int):
    """Draw a tile at screen pixel position (sx, sy) — 32x32, using sprites."""
    if tile == WATER:
        water_frame = (frame // 80) % 4
        if water_frame == 0:
            pyxel.blt(sx, sy, 0, 128, 0, 32, 32)
        else:
            pyxel.blt(sx, sy, 0, 32 * water_frame, 32, 32, 32)
    elif tile <= 7:
        pyxel.blt(sx, sy, 0, tile * 32, 0, 32, 32)
    else:  # BUSH (8)
        pyxel.blt(sx, sy, 0, 0, 32, 32, 32)


def draw_character(sx: int, sy: int, facing: Point, frame: int):
    """Draw a creature sprite at screen pixel position (32x32), using sprites."""
    walk_bob = (frame // 6) % 2
    dir_idx = {DOWN: 0, UP: 1, LEFT: 2, RIGHT: 3}[facing]
    u = (dir_idx * 2 + walk_bob) * 32
    pyxel.blt(sx, sy, 0, u, 64, 32, 32, 2)  # colkey=2 for transparency


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

    underwater = model.tilemap[py][px] == WATER

    for sy in range(VIEWPORT_H):
        for sx in range(VIEWPORT_W):
            tx = (cam_x + sx) % MAP_W
            ty = (cam_y + sy) % MAP_H
            tile = model.tilemap[ty][tx]
            if underwater and tile != WATER:
                # Can't see above-water tiles when submerged
                pyxel.rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 1)
            else:
                draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.frame)

    # Draw player at center of screen
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    draw_character(pcx, pcy, model.facing, model.frame)

    # O2 bar
    underwater = model.tilemap[py][px] == WATER
    can_auto_breathe = (model.breathing_mode == LUNGS and not underwater)
    # Show bar unless lungs mode on land with full O2
    show_o2 = not (can_auto_breathe and model.o2 >= O2_MAX)
    if show_o2:
        bar_w = 100
        bar_h = 8
        bar_x = (SCREEN_W - bar_w) // 2
        bar_y = 10
        o2_frac = model.o2 / O2_MAX
        # Background
        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 0)
        # Fill — color based on level
        fill_color = 11 if o2_frac > 0.5 else (9 if o2_frac > 0.25 else 8)
        pyxel.rect(bar_x, bar_y, int(bar_w * o2_frac), bar_h, fill_color)
        # Label
        mode_label = "LUNGS" if model.breathing_mode == LUNGS else "GILLS"
        pyxel.text(bar_x + bar_w + 4, bar_y, f"O2 [{mode_label}]", 7)

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
        f"map:{MAP_W}x{MAP_H}  o2:{model.o2 // 60}s  mode:{model.breathing_mode}",
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
        pyxel.load("pocket_world.pyxres", excl_sounds=True, excl_musics=True, excl_tilemaps=True)
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
            if pyxel.btnp(pyxel.KEY_SPACE):
                msgs.append(Breathe())
            if pyxel.btnp(pyxel.KEY_B):
                msgs.append(ToggleBreathingMode())

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
