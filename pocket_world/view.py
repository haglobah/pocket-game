import math

import arcade
from arcade.types.rect import LBWH
from pathlib import Path

from .constants import (
    SCREEN_W,
    SCREEN_H,
    TILE_SIZE,
    VIEWPORT_W,
    VIEWPORT_H,
    DEBUG_HEIGHT,
    MAP_W,
    MAP_H,
    WATER,
    WATER_DEEP,
    PORTAL,
    PLAYER_MAX_HP,
    PUNCH_COOLDOWN,
    DARK_SPRITE_MAP,
    is_swimmable,
    SAND,
    SAND_DARK,
    CLIFF,
    CLIFF_EDGE,
    PALM_TREE,
    CACTUS,
    DEAD_BUSH,
    ROCK,
    BUSH_GREEN,
    BUSH_RED,
    BUSH_YELLOW,
    GRASS,
    TALL_GRASS,
    FLOWERS,
    DIRT,
    TREE,
    BUSH,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    UP_LEFT,
    UP_RIGHT,
    DOWN_LEFT,
    DOWN_RIGHT,
    DIR_NAME,
    LUNGS,
    O2_MAX,
    HYDRATION_MAX,
    HUNGER_MAX,
    DEATH_SCREEN_MIN_FRAMES,
    REWIND_DURATION,
    THOUGHT_CHAR_SPEED,
)
from .model import Model, PlantObject, ThoughtBubble

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Pyxel 16-color palette mapped to RGBA ---
PYXEL_PALETTE = [
    (0, 0, 0, 255),               # 0  black
    (43, 51, 95, 255),             # 1  dark blue
    (126, 32, 114, 255),           # 2  dark purple
    (25, 149, 72, 255),            # 3  dark green
    (139, 72, 42, 255),            # 4  brown
    (68, 96, 169, 255),            # 5  dark grey / blue-grey
    (198, 195, 181, 255),          # 6  light grey
    (255, 241, 232, 255),          # 7  white
    (255, 0, 77, 255),             # 8  red
    (255, 163, 0, 255),            # 9  orange
    (255, 236, 39, 255),           # 10 yellow
    (0, 228, 54, 255),             # 11 green
    (41, 173, 255, 255),           # 12 blue
    (131, 118, 156, 255),          # 13 indigo / lavender
    (255, 119, 168, 255),          # 14 pink
    (255, 204, 170, 255),          # 15 peach
]


def _col(idx: int) -> tuple:
    return PYXEL_PALETTE[idx]


# --- Sprite sheet caches ---
_env_textures: dict[int, arcade.Texture] | None = None
_char_textures: list[arcade.Texture] | None = None
_dark_textures: dict[str, arcade.Texture] | None = None
_plant_textures: dict[str, arcade.Texture] | None = None
_plant_eaten_textures: dict[str, arcade.Texture] | None = None


def _load_env_textures():
    global _env_textures
    if _env_textures is not None:
        return
    sheet = arcade.SpriteSheet(str(_PROJECT_ROOT / "assets" / "sprites" / "also_without_berries.png"))
    _env_textures = {}
    tile_coords = {
        SAND: (0, 32),
        SAND_DARK: (96, 0),
        PALM_TREE: (96, 32),
        CACTUS: (64, 32),
        WATER: (0, 96),
        WATER_DEEP: (0, 64),
    }
    for tile_type, (tx, ty) in tile_coords.items():
        _env_textures[tile_type] = sheet.get_texture(LBWH(tx, ty, 32, 32))


def _load_char_textures():
    global _char_textures
    if _char_textures is not None:
        return
    sheet = arcade.SpriteSheet(str(_PROJECT_ROOT / "assets" / "sprites" / "karl_sprites.png"))
    _char_textures = []
    for i in range(8):
        _char_textures.append(sheet.get_texture(LBWH(i * 32, 64, 32, 32)))


def _load_plant_textures():
    global _plant_textures, _plant_eaten_textures
    if _plant_textures is not None:
        return
    sheet = arcade.SpriteSheet(str(_PROJECT_ROOT / "assets" / "sprites" / "also_without_berries.png"))
    _plant_textures = {}
    _plant_eaten_textures = {}
    plant_x = {"palm_tree": 96, "cactus": 64, "bush_berry": 32}
    for kind, sx in plant_x.items():
        _plant_textures[kind] = sheet.get_texture(LBWH(sx, 32, 32, 32))
        _plant_eaten_textures[kind] = sheet.get_texture(LBWH(sx + 96, 32, 32, 32))


def _load_dark_textures():
    global _dark_textures
    if _dark_textures is not None:
        return
    _dark_textures = {}
    dark_env_path = str(_PROJECT_ROOT / "assets" / "dark_pocket_world" / "dark_environment_sprites.png")
    try:
        dark_sheet = arcade.SpriteSheet(dark_env_path)
        tile_coords = {
            SAND: (0, 32),
            SAND_DARK: (96, 0),
            PALM_TREE: (96, 32),
            CACTUS: (64, 32),
            WATER: (0, 96),
            WATER_DEEP: (0, 64),
        }
        for tile_type, (tx, ty) in tile_coords.items():
            _dark_textures[f"tile_{tile_type}"] = dark_sheet.get_texture(LBWH(tx, ty, 32, 32))
    except Exception:
        pass

    dark_assets = _PROJECT_ROOT / "assets" / "dark_pocket_world"
    _all_sprites = {
        "squid": "minions/squid_left.png",
        "squid_small": "minions/squid_small_left.png",
        "scorpion": "minions/scorpion_left.png",
        "golem": "minions/golem_left.png",
        "head": "boss/head.png",
        "wings": "boss/wings.png",
        "arms": "boss/arms.png",
        "projectile_1": "boss/projectile_1.png",
        "projectile_2": "boss/projectile_2.png",
    }
    for name, relpath in _all_sprites.items():
        path = str(dark_assets / relpath)
        try:
            _dark_textures[name] = arcade.load_texture(path)
        except Exception:
            pass
    for name in ("squid", "squid_small", "scorpion", "golem", "arms"):
        if name in _all_sprites:
            path = str(dark_assets / _all_sprites[name])
            try:
                tex = arcade.load_texture(path)
                _dark_textures[f"{name}_flip"] = tex.flip_left_right()
            except Exception:
                pass


def _ensure_all_textures():
    _load_env_textures()
    _load_char_textures()
    _load_plant_textures()
    _load_dark_textures()


# Minimap
MINIMAP_SCALE = 8
MINIMAP_W = MAP_W // MINIMAP_SCALE
MINIMAP_H = MAP_H // MINIMAP_SCALE

_MINIMAP_COLORS = {
    SAND: 10, SAND_DARK: 9, CLIFF: 4, CLIFF_EDGE: 4,
    PALM_TREE: 11, CACTUS: 3, DEAD_BUSH: 9, ROCK: 13,
    WATER: 5, WATER_DEEP: 1, BUSH_GREEN: 3, BUSH_RED: 8,
    BUSH_YELLOW: 10, PORTAL: 2,
}

_minimap_cache_seed: int | None = None
_minimap_texture: arcade.Texture | None = None

_THOUGHT_FONT_SIZE = 16
_DEFAULT_FONT_HEIGHT = 10


# --- Coordinate helpers ---
# Arcade: bottom-left origin. Pyxel: top-left origin.

def _ay(pyxel_y: int) -> float:
    """Convert top-left y to arcade bottom-left y."""
    return SCREEN_H - pyxel_y


def _rect(x: int, y: int, w: int, h: int, col_idx: int):
    """Filled rect at pyxel-style top-left (x, y)."""
    color = _col(col_idx)
    # LBWH: left, bottom, width, height
    arcade.draw_lbwh_rectangle_filled(x, SCREEN_H - y - h, w, h, color)


def _rectb(x: int, y: int, w: int, h: int, col_idx: int):
    """Rect outline at pyxel-style top-left (x, y)."""
    color = _col(col_idx)
    arcade.draw_lbwh_rectangle_outline(x, SCREEN_H - y - h, w, h, color)


def _line(x1: int, y1: int, x2: int, y2: int, col_idx: int):
    color = _col(col_idx)
    arcade.draw_line(x1, _ay(y1), x2, _ay(y2), color)


def _circ(cx: int, cy: int, r: int, col_idx: int):
    color = _col(col_idx)
    arcade.draw_circle_filled(cx, _ay(cy), r, color)


def _circb(cx: int, cy: int, r: int, col_idx: int):
    color = _col(col_idx)
    arcade.draw_circle_outline(cx, _ay(cy), r, color)


def _pset(x: int, y: int, col_idx: int):
    arcade.draw_point(x, _ay(y), _col(col_idx), 1)


def _text(x: int, y: int, text_str: str, col_idx: int, font_size: int = 10):
    color = _col(col_idx)
    # draw_text anchor_y default is "baseline"; use "top" for pyxel-style coords
    arcade.draw_text(text_str, x, _ay(y), color, font_size, anchor_y="top")


def _text_width(text_str: str, font_size: int = 10) -> int:
    return int(len(text_str) * font_size * 0.6)


def _blt(sx: int, sy: int, texture: arcade.Texture):
    """Draw a texture at pyxel-style top-left coordinates."""
    w = texture.width
    h = texture.height
    rect = LBWH(sx, SCREEN_H - sy - h, w, h)
    arcade.draw_texture_rect(texture, rect)


def _blt_scaled(sx: int, sy: int, texture: arcade.Texture, w: int, h: int, flip_h: bool = False):
    """Draw a texture scaled to w x h at pyxel-style top-left coordinates."""
    tex = texture
    if flip_h:
        tex = texture.flip_left_right()
    rect = LBWH(sx, SCREEN_H - sy - h, w, h)
    arcade.draw_texture_rect(tex, rect)


def draw_tile(sx: int, sy: int, tile: int, frame: int, dark: bool = False):
    """Draw a 32x32 tile at screen pixel position (sx, sy) in pyxel coords."""
    if dark and _dark_textures:
        tex = _dark_textures.get(f"tile_{tile}")
        if tex:
            _blt(sx, sy, tex)
            return
    elif _env_textures:
        tex = _env_textures.get(tile)
        if tex:
            _blt(sx, sy, tex)
            return

    # Fallback: procedural drawing
    if tile == SAND:
        _rect(sx, sy, 32, 32, 10)
    elif tile == SAND_DARK:
        _rect(sx, sy, 32, 32, 9)
    elif tile == CLIFF:
        _rect(sx, sy, 32, 32, 4)
        for i in range(5):
            lx = ((sx * 3 + i * 19 + sy) % 24) + sx + 2
            ly = ((sy * 7 + i * 13 + sx) % 24) + sy + 4
            _line(lx, ly, lx + 5, ly + 1, 2)
        for i in range(3):
            dx = ((sx + i * 23) * 11 + sy * 5) % 26 + 3
            dy = ((sy + i * 19) * 7 + sx) % 26 + 3
            _pset(sx + dx, sy + dy, 13)
    elif tile == CLIFF_EDGE:
        _rect(sx, sy, 32, 32, 9)
        _rect(sx, sy, 32, 8, 4)
        _rect(sx + 4, sy + 8, 24, 4, 4)
        for i in range(6):
            dx = ((sx + i * 11) % 28) + 2
            _pset(sx + dx, sy + 12, 4)
    elif tile == PALM_TREE:
        _rect(sx, sy, 32, 32, 10)
    elif tile == CACTUS:
        _rect(sx, sy, 32, 32, 10)
    elif tile == DEAD_BUSH:
        _rect(sx, sy, 32, 32, 10)
        cx, cy = sx + 16, sy + 24
        _line(cx, cy, cx - 6, cy - 10, 4)
        _line(cx, cy, cx + 5, cy - 8, 4)
        _line(cx, cy, cx - 2, cy - 12, 9)
        _line(cx - 6, cy - 10, cx - 10, cy - 14, 4)
        _line(cx + 5, cy - 8, cx + 9, cy - 12, 9)
        _line(cx - 2, cy - 12, cx - 4, cy - 16, 4)
    elif tile == ROCK:
        _rect(sx, sy, 32, 32, 10)
        _circ(sx + 16, sy + 22, 8, 13)
        _circ(sx + 14, sy + 20, 6, 7)
        _circ(sx + 18, sy + 24, 5, 5)
    elif tile == WATER:
        _rect(sx, sy, 32, 32, 5)
    elif tile == WATER_DEEP:
        _rect(sx, sy, 32, 32, 1)
    elif tile == BUSH_GREEN:
        _rect(sx, sy, 32, 32, 10)
        _circ(sx + 16, sy + 20, 9, 3)
        _circ(sx + 12, sy + 18, 7, 11)
        _circ(sx + 20, sy + 17, 6, 3)
        _circ(sx + 16, sy + 14, 5, 11)
    elif tile == BUSH_RED:
        _rect(sx, sy, 32, 32, 10)
        _circ(sx + 16, sy + 20, 9, 3)
        _circ(sx + 12, sy + 17, 6, 11)
        _circ(sx + 20, sy + 17, 6, 3)
        _circ(sx + 10, sy + 15, 2, 8)
        _circ(sx + 18, sy + 13, 2, 8)
        _circ(sx + 22, sy + 16, 2, 8)
        _circ(sx + 14, sy + 12, 2, 8)
        _pset(sx + 10, sy + 15, 2)
        _pset(sx + 18, sy + 13, 2)
    elif tile == BUSH_YELLOW:
        _rect(sx, sy, 32, 32, 10)
        _circ(sx + 16, sy + 20, 9, 3)
        _circ(sx + 12, sy + 17, 6, 11)
        _circ(sx + 20, sy + 17, 6, 3)
        _circ(sx + 10, sy + 15, 2, 10)
        _circ(sx + 18, sy + 13, 2, 10)
        _circ(sx + 22, sy + 16, 2, 10)
        _circ(sx + 14, sy + 12, 2, 10)
        _pset(sx + 10, sy + 15, 9)
        _pset(sx + 18, sy + 13, 9)
    elif tile == PORTAL:
        _rect(sx, sy, 32, 32, 0)
        anim = (frame // 8) % 5
        r_outer = 14
        r_inner = 8
        cx, cy = sx + 16, sy + 16
        portal_colors = (2, 5, 12, 6, 13)
        _circ(cx, cy, r_outer, portal_colors[anim])
        _circ(cx, cy, r_inner, portal_colors[(anim + 2) % 5])
        _circ(cx, cy, 4, 0)
        for i in range(6):
            angle = (frame * 0.05 + i * 1.047)
            lx = cx + int(math.cos(angle) * r_outer)
            ly = cy + int(math.sin(angle) * r_outer)
            _pset(lx, ly, 7)


def draw_plant(sx: int, sy: int, obj: PlantObject):
    if _plant_textures and obj.kind in _plant_textures:
        if obj.has_fruit:
            _blt(sx, sy, _plant_textures[obj.kind])
        else:
            _blt(sx, sy, _plant_eaten_textures[obj.kind])
    else:
        _rect(sx, sy, 32, 32, 3 if obj.has_fruit else 9)


def draw_character(sx: int, sy: int, facing, frame: int):
    walk_bob = (frame // 6) % 2
    dir_idx = {
        DOWN: 0, DOWN_LEFT: 0, DOWN_RIGHT: 0,
        UP: 1, UP_LEFT: 1, UP_RIGHT: 1,
        LEFT: 2, RIGHT: 3,
    }.get(facing, 0)
    tex_idx = dir_idx * 2 + walk_bob
    if _char_textures and tex_idx < len(_char_textures):
        _blt(sx, sy, _char_textures[tex_idx])
    else:
        _rect(sx, sy, 32, 32, 11)


def view(model: Model):
    _ensure_all_textures()
    if model.game.state == "title":
        view_title(model)
    elif model.game.state == "dead":
        view_death(model)
    elif model.game.state == "rewind":
        view_rewind(model)
    elif model.game.state == "dark_play":
        view_dark_play(model)
    elif model.game.state == "ending_b":
        view_ending_b(model)
    else:
        view_play(model)


def _center_text(y: int, text_str: str, col_idx: int, font_size: int = 24):
    width = _text_width(text_str, font_size)
    x = (SCREEN_W - width) // 2
    _text(x, y, text_str, col_idx, font_size)


def view_title(model: Model):
    arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, SCREEN_H, _col(1))

    _center_text(260, "POCKET WORLD", 7, 40)
    _center_text(320, "Enter seed (or press ENTER for random):", 13, 24)

    input_text = model.game.seed_input + ("_" if (model.game.frame // 20) % 2 == 0 else " ")
    _center_text(350, input_text, 7, 24)

    _center_text(390, "[ENTER] Start", 6, 24)

    draw_character(SCREEN_W // 2 - 16, 210, DOWN, model.game.frame)


def view_death(model: Model):
    arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, SCREEN_H, _col(0))
    y = 120

    _center_text(y, f"Cycle {model.cycle.number} -- You died", 8, 24)
    y += 36

    _center_text(y, f"Seed: {model.map.seed}", 13, 24)
    y += 26

    _center_text(y, f"Reason: {model.cycle.death_reason}", 8, 24)
    y += 42

    if model.cycle.learned:
        _center_text(y, "In this cycle, you learned:", 7, 24)
        y += 22
        for skill in model.cycle.learned:
            _center_text(y, f"- {skill}", 11, 24)
            y += 18
    else:
        _center_text(y, "You didn't learn anything this cycle.", 13, 24)
    y += 30

    if model.cycle.death_timer >= DEATH_SCREEN_MIN_FRAMES:
        blink = (model.cycle.death_timer // 30) % 2 == 0
        if blink:
            _center_text(y, "[ENTER] Continue", 7, 24)


def _draw_hourglass(cx: int, cy: int, fill_frac: float):
    hw, hh = 20, 40
    for i in range(hh):
        if i < hh // 2:
            w = int(hw * (1 - i / (hh // 2)))
            sand_h = int((hh // 2) * (1.0 - fill_frac))
            col = 9 if i < sand_h else 0
        else:
            j = i - hh // 2
            w = int(hw * (j / (hh // 2)))
            sand_h = int((hh // 2) * fill_frac)
            rows_from_bottom = hh - 1 - i
            col = 9 if rows_from_bottom < sand_h else 0
        if w > 0:
            _rect(cx - w, cy - hh // 2 + i, w * 2, 1, col)
    _line(cx - hw, cy - hh // 2, cx + hw, cy - hh // 2, 7)
    _line(cx - hw, cy + hh // 2, cx + hw, cy + hh // 2, 7)
    _line(cx - hw, cy - hh // 2, cx, cy, 7)
    _line(cx + hw, cy - hh // 2, cx, cy, 7)
    _line(cx - hw, cy + hh // 2, cx, cy, 7)
    _line(cx + hw, cy + hh // 2, cx, cy, 7)


def view_rewind(model: Model):
    arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, SCREEN_H, _col(0))
    fill_frac = 1.0 - (model.cycle.rewind_timer / REWIND_DURATION)
    _draw_hourglass(SCREEN_W // 2, SCREEN_H // 2 - 20, fill_frac)
    _center_text(SCREEN_H // 2 + 50, "Rewinding...", 7)
    _center_text(SCREEN_H // 2 + 70, f"Cycle {model.cycle.number + 1}", 13)


def _wrap_text_by_width(text_str: str, max_width: int, font_size: int = 16) -> list[str]:
    words = text_str.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and _text_width(candidate, font_size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_thought_bubble(cx: int, bottom_y: int, thought: ThoughtBubble):
    chars_shown = min(len(thought.text), thought.timer // THOUGHT_CHAR_SPEED)
    display_text = thought.text[:chars_shown]
    if not display_text:
        return

    font_size = _THOUGHT_FONT_SIZE
    max_text_w = 240
    lines = _wrap_text_by_width(display_text, max_text_w, font_size)
    line_h = font_size + 4

    text_w = max(_text_width(line, font_size) for line in lines)
    text_h = len(lines) * line_h - 2

    pad_x, pad_y = 8, 6
    bw = text_w + pad_x * 2
    bh = text_h + pad_y * 2
    bx = cx - bw // 2
    by = bottom_y - bh - 16

    bx = max(2, min(bx, SCREEN_W - bw - 2))

    # Rounded rectangle fill
    _rect(bx + 2, by + 1, bw - 4, bh - 2, 7)
    _rect(bx + 1, by + 2, bw - 2, bh - 4, 7)

    # Border
    _line(bx + 2, by, bx + bw - 3, by, 5)
    _line(bx + 2, by + bh - 1, bx + bw - 3, by + bh - 1, 5)
    _line(bx, by + 2, bx, by + bh - 3, 5)
    _line(bx + bw - 1, by + 2, bx + bw - 1, by + bh - 3, 5)
    _pset(bx + 1, by + 1, 5)
    _pset(bx + bw - 2, by + 1, 5)
    _pset(bx + 1, by + bh - 2, 5)
    _pset(bx + bw - 2, by + bh - 2, 5)

    # Tail dots
    dot_x = cx
    _circ(dot_x - 2, by + bh + 4, 3, 7)
    _circb(dot_x - 2, by + bh + 4, 3, 5)
    _circ(dot_x + 2, by + bh + 10, 2, 7)
    _circb(dot_x + 2, by + bh + 10, 2, 5)

    # Text
    ty = by + pad_y
    for line in lines:
        lx = bx + pad_x
        _text(lx, ty, line, 1, font_size)
        ty += line_h


def _ensure_minimap(model: Model):
    global _minimap_cache_seed, _minimap_texture
    if _minimap_cache_seed == model.map.seed:
        return
    from PIL import Image as PILImage
    img = PILImage.new("RGBA", (MINIMAP_W, MINIMAP_H), (0, 0, 0, 255))
    pixels = img.load()
    for my in range(MINIMAP_H):
        ty = my * MINIMAP_SCALE
        for mx in range(MINIMAP_W):
            tx = mx * MINIMAP_SCALE
            tile = model.map.tilemap[ty][tx]
            col_idx = _MINIMAP_COLORS.get(tile, 0)
            pixels[mx, my] = PYXEL_PALETTE[col_idx]
    _minimap_texture = arcade.Texture(img, hash=f"minimap_{model.map.seed}")
    _minimap_cache_seed = model.map.seed


def _draw_minimap(model: Model):
    _ensure_minimap(model)
    if _minimap_texture is None:
        return
    mx = SCREEN_W - MINIMAP_W - 4
    my = VIEWPORT_H * TILE_SIZE - MINIMAP_H - 4
    _rect(mx - 2, my - 2, MINIMAP_W + 4, MINIMAP_H + 4, 0)
    _rectb(mx - 2, my - 2, MINIMAP_W + 4, MINIMAP_H + 4, 7)
    _blt(mx, my, _minimap_texture)
    # Player dot
    px = model.player.pos.x // MINIMAP_SCALE
    py = model.player.pos.y // MINIMAP_SCALE
    dot_col = 8 if (model.game.frame // 15) % 2 == 0 else 7
    _rect(mx + px - 1, my + py - 1, 3, 3, dot_col)
    _text(mx + MINIMAP_W - _text_width("[M] Map", 10), my - 10, "[M] Map", 7, 10)


def view_play(model: Model):
    arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, SCREEN_H, _col(0))
    px, py = model.player.pos

    cam_x = px - VIEWPORT_W // 2
    cam_y = py - VIEWPORT_H // 2

    underwater = is_swimmable(model.map.tilemap[py][px])

    for sy in range(VIEWPORT_H):
        for sx in range(VIEWPORT_W):
            tx = cam_x + sx
            ty = cam_y + sy
            if tx < 0 or tx >= MAP_W or ty < 0 or ty >= MAP_H:
                _rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 0)
                continue
            tile = model.map.tilemap[ty][tx]
            if underwater and not is_swimmable(tile):
                _rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 1)
            else:
                draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.game.frame)

    # Draw plant objects visible in the viewport
    for obj in model.map.objects:
        ox = obj.anchor.x - cam_x
        oy = obj.anchor.y - cam_y
        if 0 <= ox < VIEWPORT_W and 0 <= oy < VIEWPORT_H:
            draw_plant(ox * TILE_SIZE, oy * TILE_SIZE, obj)

    # Draw player at center
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    draw_character(pcx, pcy, model.player.facing, model.game.frame)

    # Thought bubble above player
    if model.game.thought is not None:
        player_cx = pcx + TILE_SIZE // 2
        player_top = pcy
        _draw_thought_bubble(player_cx, player_top - 6, model.game.thought)

    # Status bars
    bar_w = 140
    bar_h = 12
    bar_x = (SCREEN_W - bar_w) // 2
    bar_y = 10

    def _draw_bar(y: int, frac: float, label: str, full_col: int, mid_col: int, low_col: int):
        col = full_col if frac > 0.5 else (mid_col if frac > 0.25 else low_col)
        _rect(bar_x - 1, y - 1, bar_w + 2, bar_h + 2, 0)
        _rect(bar_x, y, int(bar_w * frac), bar_h, col)
        _text(bar_x + bar_w + 4, y, label, 7, 16)

    # O2 bar
    underwater = is_swimmable(model.map.tilemap[py][px])
    can_auto_breathe = model.player.breathing_mode == LUNGS and not underwater
    show_o2 = not (can_auto_breathe and model.player.o2 >= O2_MAX)
    if show_o2:
        mode_label = "LUNGS" if model.player.breathing_mode == LUNGS else "GILLS"
        _draw_bar(bar_y, model.player.o2 / O2_MAX, f"O2 [{mode_label}]", 11, 9, 8)
        bar_y += bar_h + 4

    # Hydration bar
    _draw_bar(bar_y, model.player.hydration / HYDRATION_MAX, "Water [Q]", 12, 6, 8)
    bar_y += bar_h + 4

    # Hunger bar
    _draw_bar(bar_y, model.player.hunger / HUNGER_MAX, "Food [E]", 11, 9, 8)

    # Minimap overlay
    if model.game.show_minimap:
        _draw_minimap(model)

    # Debug panel below map
    map_bottom = VIEWPORT_H * TILE_SIZE
    _rect(0, map_bottom, SCREEN_W, DEBUG_HEIGHT, 0)
    tile_name = {
        GRASS: "grass", TALL_GRASS: "tall_grass", FLOWERS: "flowers",
        DIRT: "dirt", WATER: "water", SAND: "sand", TREE: "tree",
        ROCK: "rock", BUSH: "bush",
    }
    standing_on = tile_name.get(model.map.tilemap[py][px], "?")
    y = map_bottom + 2
    lines = [
        f"seed:{model.map.seed}  state:{model.game.state}",
        f"pos:({px},{py})  facing:{DIR_NAME.get(model.player.facing, '?')}  tile:{standing_on}",
        f"move_timer:{model.player.move_timer}  frame:{model.game.frame}",
        f"o2:{model.player.o2 // 60}s  water:{model.player.hydration // 60}s  food:{model.player.hunger // 60}s  mode:{model.player.breathing_mode}",
    ]
    for line in lines:
        _text(2, y, line, 7, 10)
        y += _DEFAULT_FONT_HEIGHT + 2


# ---------------------------------------------------------------------------
# Dark Pocket World view
# ---------------------------------------------------------------------------

_BOSS_SPRITE_KEYS = {
    "head": "head",
    "wings": "wings",
    "arms_left": "arms",
    "arms_right": "arms",
}


def view_dark_play(model: Model):
    global _minimap_cache_seed
    _minimap_cache_seed = None
    arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, SCREEN_H, _col(0))
    dw = model.dark_world
    if dw is None:
        return

    px, py = model.player.pos
    cam_x = px - VIEWPORT_W // 2
    cam_y = py - VIEWPORT_H // 2

    tilemap = model.map.tilemap
    for sy in range(VIEWPORT_H):
        for sx in range(VIEWPORT_W):
            tx = cam_x + sx
            ty = cam_y + sy
            if tx < 0 or tx >= MAP_W or ty < 0 or ty >= MAP_H:
                _rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 0)
                continue
            tile = tilemap[ty][tx]
            draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.game.frame, dark=True)

    # Draw boss parts
    _BOSS_Z_ORDER = ("wings", "arms_left", "arms_right", "head")
    parts_by_name = {p.name: p for p in dw.boss.parts}
    frame = model.game.frame
    arm_sway = int(math.sin(frame * 0.03) * 4)
    for name in _BOSS_Z_ORDER:
        part = parts_by_name.get(name)
        if part is None or part.hp <= 0:
            continue
        bx = (part.pos.x - cam_x) * TILE_SIZE
        by = (part.pos.y - cam_y) * TILE_SIZE
        bw = part.size.x * TILE_SIZE
        bh = part.size.y * TILE_SIZE
        if name == "arms_left":
            bx -= arm_sway
        elif name == "arms_right":
            bx += arm_sway
        sprite_key = _BOSS_SPRITE_KEYS.get(name)
        if sprite_key and _dark_textures and sprite_key in _dark_textures:
            tex = _dark_textures[sprite_key]
            flip_h = name == "arms_right"
            _blt_scaled(bx, by, tex, bw, bh, flip_h=flip_h)
        else:
            _rect(bx, by, bw, bh, 8)

    # Draw projectiles
    for proj in dw.projectiles:
        proj_sx = (proj.pos.x - cam_x) * TILE_SIZE
        proj_sy = (proj.pos.y - cam_y) * TILE_SIZE
        pkey = "projectile_1" if (model.game.frame // 6) % 2 == 0 else "projectile_2"
        if _dark_textures and pkey in _dark_textures:
            _blt(proj_sx, proj_sy, _dark_textures[pkey])
        else:
            _circ(proj_sx + 16, proj_sy + 16, 8, 8)

    # Draw minions
    for m in dw.minions:
        if m.hp <= 0:
            continue
        mmx = (m.pos.x - cam_x) * TILE_SIZE
        mmy = (m.pos.y - cam_y) * TILE_SIZE
        if _dark_textures and m.kind in _dark_textures:
            flip_key = f"{m.kind}_flip"
            if m.facing.x >= 0 and flip_key in _dark_textures:
                tex = _dark_textures[flip_key]
            else:
                tex = _dark_textures[m.kind]
            _blt_scaled(mmx, mmy, tex, TILE_SIZE * 2, TILE_SIZE * 2)
        else:
            _rect(mmx, mmy, TILE_SIZE, TILE_SIZE, 2)

    # Draw player
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    if model.player.invincible_timer > 0 and (model.game.frame // 4) % 2 == 0:
        pass  # blink
    else:
        draw_character(pcx, pcy, model.player.facing, model.game.frame)

    # Punch visual
    if model.player.punch_timer > PUNCH_COOLDOWN - 4:
        f = model.player.facing
        for i in range(1, 3):
            flash_x = pcx + f.x * i * TILE_SIZE + TILE_SIZE // 2
            flash_y = pcy + f.y * i * TILE_SIZE + TILE_SIZE // 2
            _circ(flash_x, flash_y, 6, 10)
            _circ(flash_x, flash_y, 3, 7)

    # HUD: Player HP
    hud_y = 6
    for i in range(PLAYER_MAX_HP):
        hx = 8 + i * 18
        col = 8 if i < model.player.hp else 1
        _rect(hx, hud_y, 14, 14, col)
        _rectb(hx, hud_y, 14, 14, 7)

    # Boss status
    alive_count = sum(1 for p in dw.boss.parts if p.hp > 0)
    total_count = len(dw.boss.parts)
    status = f"Boss: {alive_count}/{total_count} parts"
    _text(SCREEN_W - _text_width(status, 16) - 8, hud_y + 2, status, 7, 16)

    # Controls hint at bottom
    map_bottom = VIEWPORT_H * TILE_SIZE
    _rect(0, map_bottom, SCREEN_W, DEBUG_HEIGHT, 0)
    _text(2, map_bottom + 2, f"HP:{model.player.hp}/{PLAYER_MAX_HP}  [F] Punch  [WASD/Arrows] Move", 7, 10)
    _text(2, map_bottom + 12, f"Boss parts alive: {alive_count}/{total_count}  Minions: {len([m for m in dw.minions if m.hp > 0])}", 7, 10)


def view_ending_b(model: Model):
    arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, SCREEN_H, _col(0))

    _center_text(140, "YOU SAVED THE", 7, 40)
    _center_text(190, "POCKET WORLD", 11, 40)

    _center_text(260, "The dark pocket world has been defeated.", 13, 24)
    _center_text(290, "The stolen land returns to its rightful place.", 13, 24)
    _center_text(320, "Peace is restored.", 7, 24)

    _center_text(380, "-- ENDING B --", 14, 24)

    blink = (model.game.frame // 30) % 2 == 0
    if blink:
        _center_text(430, "[ENTER] Return to Title", 7, 24)
