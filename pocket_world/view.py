import math

import pyxel
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
    WISE_DIALOG_CHAR_SPEED,
)
from .model import Model, PlantObject, ThoughtBubble


_TITLE_FONT = None
_UI_FONT = None
_HUD_FONT = None
_THOUGHT_FONT = None

_THOUGHT_FONT_SIZE = 16


def _load_ui_font(filename: str, size: float):
    """Load a UI font from the installed pyxel package; fallback to default font if unavailable."""
    try:
        pyxel_dir = Path(pyxel.__file__).resolve().parent
        font_path = pyxel_dir / "examples" / "assets" / filename
        if font_path.exists():
            return pyxel.Font(str(font_path), size)
    except Exception:
        pass
    return None


def _get_title_font():
    global _TITLE_FONT
    if _TITLE_FONT is None:
        _TITLE_FONT = _load_ui_font("PixelMplus12-Regular.ttf", 40)
    return _TITLE_FONT


def _get_ui_font():
    global _UI_FONT
    if _UI_FONT is None:
        _UI_FONT = _load_ui_font("PixelMplus12-Regular.ttf", 24)
    return _UI_FONT


def _get_hud_font():
    global _HUD_FONT
    if _HUD_FONT is None:
        _HUD_FONT = _load_ui_font("PixelMplus12-Regular.ttf", 16)
    return _HUD_FONT


def _get_thought_font():
    global _THOUGHT_FONT
    if _THOUGHT_FONT is None:
        _THOUGHT_FONT = _load_ui_font("PixelMplus12-Regular.ttf", _THOUGHT_FONT_SIZE)
    return _THOUGHT_FONT


# Minimap: 1 pixel per 8 tiles → 250x125 pixels
MINIMAP_SCALE = 8
MINIMAP_W = MAP_W // MINIMAP_SCALE  # 250
MINIMAP_H = MAP_H // MINIMAP_SCALE  # 125

# Color mapping for minimap pixels
_MINIMAP_COLORS = {
    SAND: 10,
    SAND_DARK: 9,
    CLIFF: 4,
    CLIFF_EDGE: 4,
    PALM_TREE: 11,
    CACTUS: 3,
    DEAD_BUSH: 9,
    ROCK: 13,
    WATER: 5,
    WATER_DEEP: 1,
    BUSH_GREEN: 3,
    BUSH_RED: 8,
    BUSH_YELLOW: 10,
    PORTAL: 2,
}

# Cache the seed for which image bank 2 has been written
_minimap_cache_seed: int | None = None


def draw_tile(sx: int, sy: int, tile: int, frame: int, bank: int = 1):
    """Draw a 32x32 desert tile at screen pixel position (sx, sy)."""
    if tile == SAND:
        pyxel.blt(sx, sy, bank, 0, 32, 32, 32)
        # # Light sand base
        # pyxel.rect(sx, sy, 32, 32, 10)
        # # Subtle dot pattern for texture
        # for i in range(3):
        #     dx = ((sx + i * 13) * 7 + sy * 3) % 28 + 2
        #     dy = ((sy + i * 11) * 5 + sx * 7) % 28 + 2
        #     pyxel.pset(sx + dx, sy + dy, 9)
    elif tile == SAND_DARK:
        # Darker sand with ripple texture
        pyxel.blt(sx, sy, bank, 96, 0, 32, 32)
        # pyxel.rect(sx, sy, 32, 32, 9)
        # for i in range(4):
        #     dx = ((sx + i * 17) * 3 + sy) % 26 + 3
        #     dy = ((sy + i * 7) * 11 + sx * 3) % 26 + 3
        #     pyxel.pset(sx + dx, sy + dy, 10)
    elif tile == CLIFF:
        # Rocky cliff - dark brown with texture
        pyxel.rect(sx, sy, 32, 32, 4)
        # Rock texture lines
        for i in range(5):
            lx = ((sx * 3 + i * 19 + sy) % 24) + sx + 2
            ly = ((sy * 7 + i * 13 + sx) % 24) + sy + 4
            pyxel.line(lx, ly, lx + 5, ly + 1, 2)
        # Highlight spots
        for i in range(3):
            dx = ((sx + i * 23) * 11 + sy * 5) % 26 + 3
            dy = ((sy + i * 19) * 7 + sx) % 26 + 3
            pyxel.pset(sx + dx, sy + dy, 13)
    elif tile == CLIFF_EDGE:
        # Transition: sand base with cliff edge marks
        pyxel.rect(sx, sy, 32, 32, 9)
        # Rocky top edge
        pyxel.rect(sx, sy, 32, 8, 4)
        pyxel.rect(sx + 4, sy + 8, 24, 4, 4)
        for i in range(6):
            dx = ((sx + i * 11) % 28) + 2
            pyxel.pset(sx + dx, sy + 12, 4)
    elif tile == PALM_TREE:
        pyxel.blt(sx, sy, bank, 96, 32, 32, 32)
        # # Sand base
        # pyxel.rect(sx, sy, 32, 32, 10)
        # # Trunk
        # pyxel.rect(sx + 14, sy + 12, 4, 20, 4)
        # pyxel.rect(sx + 15, sy + 14, 2, 16, 2)
        # # Fronds (green leaf clusters)
        # pyxel.circ(sx + 16, sy + 10, 8, 3)
        # pyxel.circ(sx + 10, sy + 6, 5, 11)
        # pyxel.circ(sx + 22, sy + 6, 5, 11)
        # pyxel.circ(sx + 16, sy + 3, 5, 3)
        # # Coconuts
        # pyxel.circ(sx + 13, sy + 11, 2, 4)
        # pyxel.circ(sx + 19, sy + 11, 2, 9)
    elif tile == CACTUS:
        pyxel.blt(sx, sy, bank, 64, 32, 32, 32)
        # # Sand base
        # pyxel.rect(sx, sy, 32, 32, 10)
        # # Main cactus body
        # pyxel.rect(sx + 12, sy + 8, 8, 22, 3)
        # pyxel.rect(sx + 13, sy + 9, 6, 20, 11)
        # # Left arm
        # pyxel.rect(sx + 6, sy + 12, 6, 6, 3)
        # pyxel.rect(sx + 6, sy + 10, 4, 4, 3)
        # pyxel.rect(sx + 7, sy + 13, 4, 4, 11)
        # # Right arm
        # pyxel.rect(sx + 20, sy + 16, 6, 6, 3)
        # pyxel.rect(sx + 22, sy + 14, 4, 4, 3)
        # pyxel.rect(sx + 21, sy + 17, 4, 4, 11)
    elif tile == DEAD_BUSH:
        # Sand base with dried bush
        pyxel.rect(sx, sy, 32, 32, 10)
        # Small dried bush
        cx, cy = sx + 16, sy + 24
        pyxel.line(cx, cy, cx - 6, cy - 10, 4)
        pyxel.line(cx, cy, cx + 5, cy - 8, 4)
        pyxel.line(cx, cy, cx - 2, cy - 12, 9)
        pyxel.line(cx - 6, cy - 10, cx - 10, cy - 14, 4)
        pyxel.line(cx + 5, cy - 8, cx + 9, cy - 12, 9)
        pyxel.line(cx - 2, cy - 12, cx - 4, cy - 16, 4)
    elif tile == ROCK:
        # Sand base with a boulder
        pyxel.rect(sx, sy, 32, 32, 10)
        # Rock shape
        pyxel.circ(sx + 16, sy + 22, 8, 13)
        pyxel.circ(sx + 14, sy + 20, 6, 7)
        pyxel.circ(sx + 18, sy + 24, 5, 5)
    elif tile == WATER:
        pyxel.blt(sx, sy, bank, 0, 96, 32, 32)
        # Shallow oasis water — light blue with wave lines
        # water_frame = (frame // 80) % 4
        # c1, c2 = 5, 12
        # if water_frame % 2 == 0:
        #     c1, c2 = c2, c1
        # pyxel.rect(sx, sy, 32, 32, c1)
        # for i in range(3):
        #     wy = sy + 6 + i * 10 + (water_frame * 3) % 8
        #     pyxel.line(sx + 4, wy, sx + 28, wy, c2)
    elif tile == WATER_DEEP:
        pyxel.blt(sx, sy, bank, 0, 64, 32, 32)
        # # Deep oasis water — darker blue/indigo
        # water_frame = (frame // 100) % 4
        # c1, c2 = 1, 5
        # if water_frame % 2 == 0:
        #     c1, c2 = c2, c1
        # pyxel.rect(sx, sy, 32, 32, c1)
        # for i in range(2):
        #     wy = sy + 8 + i * 14 + (water_frame * 4) % 10
        #     pyxel.line(sx + 6, wy, sx + 26, wy, c2)
    elif tile == BUSH_GREEN:
        # Lush green bush on sand
        pyxel.rect(sx, sy, 32, 32, 10)
        # Bush body
        pyxel.circ(sx + 16, sy + 20, 9, 3)
        pyxel.circ(sx + 12, sy + 18, 7, 11)
        pyxel.circ(sx + 20, sy + 17, 6, 3)
        pyxel.circ(sx + 16, sy + 14, 5, 11)
    elif tile == BUSH_RED:
        # Bush with red fruit — indicates poisonous water
        pyxel.rect(sx, sy, 32, 32, 10)
        # Bush body
        pyxel.circ(sx + 16, sy + 20, 9, 3)
        pyxel.circ(sx + 12, sy + 17, 6, 11)
        pyxel.circ(sx + 20, sy + 17, 6, 3)
        # Red fruit
        pyxel.circ(sx + 10, sy + 15, 2, 8)
        pyxel.circ(sx + 18, sy + 13, 2, 8)
        pyxel.circ(sx + 22, sy + 16, 2, 8)
        pyxel.circ(sx + 14, sy + 12, 2, 8)
        pyxel.pset(sx + 10, sy + 15, 2)
        pyxel.pset(sx + 18, sy + 13, 2)
    elif tile == BUSH_YELLOW:
        # Bush with yellow fruit — indicates poisonous water
        pyxel.rect(sx, sy, 32, 32, 10)
        # Bush body
        pyxel.circ(sx + 16, sy + 20, 9, 3)
        pyxel.circ(sx + 12, sy + 17, 6, 11)
        pyxel.circ(sx + 20, sy + 17, 6, 3)
        # Yellow fruit
        pyxel.circ(sx + 10, sy + 15, 2, 10)
        pyxel.circ(sx + 18, sy + 13, 2, 10)
        pyxel.circ(sx + 22, sy + 16, 2, 10)
        pyxel.circ(sx + 14, sy + 12, 2, 10)
        pyxel.pset(sx + 10, sy + 15, 9)
        pyxel.pset(sx + 18, sy + 13, 9)
    elif tile == PORTAL:
        pyxel.rect(sx, sy, 32, 32, 0)
        anim = (frame // 8) % 5
        r_outer = 14
        r_inner = 8
        cx, cy = sx + 16, sy + 16
        portal_colors = (2, 5, 12, 6, 13)
        pyxel.circ(cx, cy, r_outer, portal_colors[anim])
        pyxel.circ(cx, cy, r_inner, portal_colors[(anim + 2) % 5])
        pyxel.circ(cx, cy, 4, 0)
        for i in range(6):
            angle = (frame * 0.05 + i * 1.047)
            lx = cx + int(math.cos(angle) * r_outer)
            ly = cy + int(math.sin(angle) * r_outer)
            pyxel.pset(lx, ly, 7)


# Sprite x-offsets for plant kinds in the environment sprite sheet
_PLANT_SPRITE_X = {
    "palm_tree": 96,
    "cactus": 64,
    "bush_berry": 32,
}


def draw_plant(sx: int, sy: int, obj: PlantObject):
    """Draw a plant object at screen pixel position (sx, sy)."""
    sprite_x = _PLANT_SPRITE_X[obj.kind]
    if obj.has_fruit:
        # Row at y=32 in environment_sprites.png (bank 1, y=32)
        pyxel.blt(sx, sy, 1, sprite_x, 32, 32, 32)
    else:
        # Eaten state: same x, but from without_berries.png loaded at y=128
        pyxel.blt(sx, sy, 1, sprite_x + 96, 32, 32, 32)


def draw_character(sx: int, sy: int, facing, frame: int):
    """Draw a creature sprite at screen pixel position (32x32), using sprites."""
    walk_bob = (frame // 6) % 2
    dir_idx = {
        DOWN: 0,
        DOWN_LEFT: 0,
        DOWN_RIGHT: 0,
        UP: 1,
        UP_LEFT: 1,
        UP_RIGHT: 1,
        LEFT: 2,
        RIGHT: 3,
    }.get(facing, 0)
    u = (dir_idx * 2 + walk_bob) * 32
    pyxel.blt(sx, sy, 0, u, 64, 32, 32, 2)  # colkey=2 for transparency


def draw_wise_man(sx: int, sy: int, facing):
    """Draw a 16x32 wise-man sprite; white background is transparent via colkey=7."""
    if facing == LEFT:
        u = 16
    elif facing == RIGHT:
        u = 32
    else:
        u = 0
    pyxel.blt(sx, sy, 1, u, 128, 16, 32, 7)


def view(model: Model):
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


def view_title(model: Model):
    pyxel.cls(1)
    title_font = _get_title_font()
    ui_font = _get_ui_font()

    # Title
    title = "POCKET WORLD"
    _center_text(260, title, 7, title_font)

    prompt = "Enter seed (or press ENTER for random):"
    _center_text(320, prompt, 13, ui_font)

    input_text = model.game.seed_input + ("_" if (model.game.frame // 20) % 2 == 0 else " ")
    _center_text(350, input_text, 7, ui_font)

    hint = "[ENTER] Start"
    _center_text(390, hint, 6, ui_font)

    draw_character(SCREEN_W // 2 - 16, 210, DOWN, model.game.frame)


def _center_text(y: int, text: str, col: int, f=None):
    width = f.text_width(text) if f else len(text) * pyxel.FONT_WIDTH
    x = (SCREEN_W - width) // 2
    if f:
        pyxel.text(x, y, text, col, f)
    else:
        pyxel.text(x, y, text, col)


def view_death(model: Model):
    pyxel.cls(0)
    ui_font = _get_ui_font()
    y = 120

    _center_text(y, f"Cycle {model.cycle.number} -- You died", 8, ui_font)
    y += 36

    _center_text(y, f"Seed: {model.map.seed}", 13, ui_font)
    y += 26

    _center_text(y, f"Reason: {model.cycle.death_reason}", 8, ui_font)
    y += 42

    if model.cycle.learned:
        _center_text(y, "In this cycle, you learned:", 7, ui_font)
        y += 22
        for skill in model.cycle.learned:
            _center_text(y, f"- {skill}", 11, ui_font)
            y += 18
    else:
        _center_text(y, "You didn't learn anything this cycle.", 13, ui_font)
    y += 30

    if model.cycle.death_timer >= DEATH_SCREEN_MIN_FRAMES:
        blink = (model.cycle.death_timer // 30) % 2 == 0
        if blink:
            _center_text(y, "[ENTER] Continue", 7, ui_font)


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
            pyxel.rect(cx - w, cy - hh // 2 + i, w * 2, 1, col)
    pyxel.line(cx - hw, cy - hh // 2, cx + hw, cy - hh // 2, 7)
    pyxel.line(cx - hw, cy + hh // 2, cx + hw, cy + hh // 2, 7)
    pyxel.line(cx - hw, cy - hh // 2, cx, cy, 7)
    pyxel.line(cx + hw, cy - hh // 2, cx, cy, 7)
    pyxel.line(cx - hw, cy + hh // 2, cx, cy, 7)
    pyxel.line(cx + hw, cy + hh // 2, cx, cy, 7)


def view_rewind(model: Model):
    pyxel.cls(0)
    fill_frac = 1.0 - (model.cycle.rewind_timer / REWIND_DURATION)
    _draw_hourglass(SCREEN_W // 2, SCREEN_H // 2 - 20, fill_frac)
    _center_text(SCREEN_H // 2 + 50, "Rewinding...", 7)
    _center_text(SCREEN_H // 2 + 70, f"Cycle {model.cycle.number + 1}", 13)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Word-wrap text into lines of at most max_chars characters."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def _measure_text_width(text: str, font=None) -> int:
    return font.text_width(text) if font else len(text) * pyxel.FONT_WIDTH


def _wrap_text_by_width(text: str, max_width: int, font=None) -> list[str]:
    """Word-wrap text into lines that fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and _measure_text_width(candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_thought_bubble(cx: int, bottom_y: int, thought: ThoughtBubble):
    """Draw a thought bubble centered at cx with tail ending at bottom_y."""
    chars_shown = min(len(thought.text), thought.timer // THOUGHT_CHAR_SPEED)
    display_text = thought.text[:chars_shown]
    if not display_text:
        return

    thought_font = _get_thought_font()
    max_text_w = 240
    lines = _wrap_text_by_width(display_text, max_text_w, thought_font)
    fh = _THOUGHT_FONT_SIZE if thought_font else pyxel.FONT_HEIGHT
    line_h = fh + 4

    text_w = max(_measure_text_width(line, thought_font) for line in lines)
    text_h = len(lines) * line_h - 2

    pad_x, pad_y = 8, 6
    bw = text_w + pad_x * 2
    bh = text_h + pad_y * 2
    bx = cx - bw // 2
    by = bottom_y - bh - 16

    # Clamp to screen edges
    bx = max(2, min(bx, SCREEN_W - bw - 2))

    # Rounded rectangle — fill
    pyxel.rect(bx + 2, by + 1, bw - 4, bh - 2, 7)
    pyxel.rect(bx + 1, by + 2, bw - 2, bh - 4, 7)

    # Border
    pyxel.line(bx + 2, by, bx + bw - 3, by, 5)
    pyxel.line(bx + 2, by + bh - 1, bx + bw - 3, by + bh - 1, 5)
    pyxel.line(bx, by + 2, bx, by + bh - 3, 5)
    pyxel.line(bx + bw - 1, by + 2, bx + bw - 1, by + bh - 3, 5)
    pyxel.pset(bx + 1, by + 1, 5)
    pyxel.pset(bx + bw - 2, by + 1, 5)
    pyxel.pset(bx + 1, by + bh - 2, 5)
    pyxel.pset(bx + bw - 2, by + bh - 2, 5)

    # Tail dots (thought bubble style — two small circles leading to player)
    dot_x = cx
    pyxel.circ(dot_x - 2, by + bh + 4, 3, 7)
    pyxel.circb(dot_x - 2, by + bh + 4, 3, 5)
    pyxel.circ(dot_x + 2, by + bh + 10, 2, 7)
    pyxel.circb(dot_x + 2, by + bh + 10, 2, 5)

    # Text
    ty = by + pad_y
    for line in lines:
        lx = bx + pad_x
        pyxel.text(lx, ty, line, 1, thought_font)
        ty += line_h


def _draw_dialogue_bubble(
    cx: int,
    bottom_y: int,
    text: str,
    timer: int,
    options: tuple[str, str] | None = None,
):
    """Draw a speech bubble for NPC dialogue, using thought-bubble typography."""
    chars_shown = min(len(text), timer // WISE_DIALOG_CHAR_SPEED)
    display_text = text[:chars_shown]
    if not display_text:
        return

    thought_font = _get_thought_font()
    max_text_w = 260
    lines = _wrap_text_by_width(display_text, max_text_w, thought_font)
    if options is not None:
        lines.append("")
        lines.append(f"[1] {options[0]}")
        lines.append(f"[2] {options[1]}")
    fh = _THOUGHT_FONT_SIZE if thought_font else pyxel.FONT_HEIGHT
    line_h = fh + 4

    text_w = max(_measure_text_width(line, thought_font) for line in lines)
    text_h = len(lines) * line_h - 2

    pad_x, pad_y = 8, 6
    bw = text_w + pad_x * 2
    bh = text_h + pad_y * 2
    bx = cx - bw // 2
    by = bottom_y - bh - 16

    bx = max(2, min(bx, SCREEN_W - bw - 2))

    pyxel.rect(bx + 2, by + 1, bw - 4, bh - 2, 7)
    pyxel.rect(bx + 1, by + 2, bw - 2, bh - 4, 7)
    pyxel.line(bx + 2, by, bx + bw - 3, by, 5)
    pyxel.line(bx + 2, by + bh - 1, bx + bw - 3, by + bh - 1, 5)
    pyxel.line(bx, by + 2, bx, by + bh - 3, 5)
    pyxel.line(bx + bw - 1, by + 2, bx + bw - 1, by + bh - 3, 5)
    pyxel.pset(bx + 1, by + 1, 5)
    pyxel.pset(bx + bw - 2, by + 1, 5)
    pyxel.pset(bx + 1, by + bh - 2, 5)
    pyxel.pset(bx + bw - 2, by + bh - 2, 5)

    # Speech-tail triangle toward the wizard.
    tail_x = max(bx + 8, min(cx, bx + bw - 8))
    pyxel.tri(tail_x - 4, by + bh - 1, tail_x + 4, by + bh - 1, tail_x, by + bh + 8, 7)
    pyxel.line(tail_x - 4, by + bh - 1, tail_x, by + bh + 8, 5)
    pyxel.line(tail_x + 4, by + bh - 1, tail_x, by + bh + 8, 5)

    ty = by + pad_y
    for line in lines:
        lx = bx + pad_x
        pyxel.text(lx, ty, line, 1, thought_font)
        ty += line_h
def _ensure_minimap(model: Model):
    """Write minimap to image bank 2 if not already cached for this seed."""
    global _minimap_cache_seed
    if _minimap_cache_seed == model.map.seed:
        return
    img = pyxel.images[2]
    for my in range(MINIMAP_H):
        ty = my * MINIMAP_SCALE
        for mx in range(MINIMAP_W):
            tx = mx * MINIMAP_SCALE
            tile = model.map.tilemap[ty][tx]
            img.pset(mx, my, _MINIMAP_COLORS.get(tile, 0))
    # # Overlay plant objects on minimap
    # for obj in model.map.objects:
    #     mx = obj.anchor.x // MINIMAP_SCALE
    #     my = obj.anchor.y // MINIMAP_SCALE
    #     if 0 <= mx < MINIMAP_W and 0 <= my < MINIMAP_H:
    #         img.pset(mx, my, _PLANT_MINIMAP_COLORS.get(obj.kind, 0))
    _minimap_cache_seed = model.map.seed


def _draw_minimap(model: Model):
    """Draw minimap overlay centered on screen."""
    _ensure_minimap(model)
    # Position at lower-right of the viewport
    mx = SCREEN_W - MINIMAP_W - 4
    my = VIEWPORT_H * TILE_SIZE - MINIMAP_H - 4
    # Dark background with border
    pyxel.rect(mx - 2, my - 2, MINIMAP_W + 4, MINIMAP_H + 4, 0)
    pyxel.rectb(mx - 2, my - 2, MINIMAP_W + 4, MINIMAP_H + 4, 7)
    # Blit the precomputed minimap from image bank 2
    pyxel.blt(mx, my, 2, 0, 0, MINIMAP_W, MINIMAP_H)
    # Player dot (blinking)
    px = model.player.pos.x // MINIMAP_SCALE
    py = model.player.pos.y // MINIMAP_SCALE
    dot_col = 8 if (model.game.frame // 15) % 2 == 0 else 7
    pyxel.rect(mx + px - 1, my + py - 1, 3, 3, dot_col)
    # Label
    pyxel.text(
        mx + MINIMAP_W - len("[M] Map") * pyxel.FONT_WIDTH, my - 10, "[M] Map", 7
    )


def view_play(model: Model):
    pyxel.cls(0)
    px, py = model.player.pos

    cam_x = px - VIEWPORT_W // 2
    cam_y = py - VIEWPORT_H // 2

    underwater = is_swimmable(model.map.tilemap[py][px])

    for sy in range(VIEWPORT_H):
        for sx in range(VIEWPORT_W):
            tx = cam_x + sx
            ty = cam_y + sy
            # Don't wrap - show black beyond map edges
            if tx < 0 or tx >= MAP_W or ty < 0 or ty >= MAP_H:
                pyxel.rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 0)
                continue
            tile = model.map.tilemap[ty][tx]
            if underwater and not is_swimmable(tile):
                pyxel.rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 1)
            else:
                draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.game.frame)

    # Draw plant objects visible in the viewport
    for obj in model.map.objects:
        ox = obj.anchor.x - cam_x
        oy = obj.anchor.y - cam_y
        if 0 <= ox < VIEWPORT_W and 0 <= oy < VIEWPORT_H:
            draw_plant(ox * TILE_SIZE, oy * TILE_SIZE, obj)

    # Draw wise man in world space at his spawn-adjacent tile.
    wise = model.map.wise_man
    if cam_x <= wise.x < cam_x + VIEWPORT_W and cam_y <= wise.y < cam_y + VIEWPORT_H:
        wise_sx = (wise.x - cam_x) * TILE_SIZE + (TILE_SIZE - 16) // 2
        wise_sy = (wise.y - cam_y) * TILE_SIZE
        if px < wise.x:
            wise_facing = LEFT
        elif px > wise.x:
            wise_facing = RIGHT
        else:
            wise_facing = DOWN
        draw_wise_man(wise_sx, wise_sy, wise_facing)
        if model.game.wise_dialogue is not None:
            wise_cx = wise_sx + 8
            wise_top = wise_sy
            _draw_dialogue_bubble(
                wise_cx,
                wise_top - 6,
                model.game.wise_dialogue.text,
                model.game.wise_dialogue.timer,
                model.game.wise_options if model.game.wise_dialogue_active else None,
            )

    # Hostile wizard projectiles (drawn as blue pixels and a bright core).
    for shot in model.game.wizard_shots:
        shot_sx = int(shot.x - cam_x * TILE_SIZE)
        shot_sy = int(shot.y - cam_y * TILE_SIZE)
        if 0 <= shot_sx < SCREEN_W and 0 <= shot_sy < VIEWPORT_H * TILE_SIZE:
            pyxel.pset(shot_sx, shot_sy, 12)
            pyxel.pset(shot_sx + 1, shot_sy, 5)

    # Draw player at center of screen
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    draw_character(pcx, pcy, model.player.facing, model.game.frame)

    # Thought bubble above player
    if model.game.thought is not None:
        player_cx = pcx + TILE_SIZE // 2
        player_top = pcy
        _draw_thought_bubble(player_cx, player_top - 6, model.game.thought)

    # Status bars
    hud_font = _get_hud_font()
    bar_w = 140
    bar_h = 12
    bar_x = (SCREEN_W - bar_w) // 2
    bar_y = 10

    def _draw_bar(
        y: int, frac: float, label: str, full_col: int, mid_col: int, low_col: int
    ):
        col = full_col if frac > 0.5 else (mid_col if frac > 0.25 else low_col)
        pyxel.rect(bar_x - 1, y - 1, bar_w + 2, bar_h + 2, 0)
        pyxel.rect(bar_x, y, int(bar_w * frac), bar_h, col)
        pyxel.text(bar_x + bar_w + 4, y, label, 7, hud_font)

    # O2 bar (hidden when lungs on land and full)
    underwater = is_swimmable(model.map.tilemap[py][px])
    can_auto_breathe = model.player.breathing_mode == LUNGS and not underwater
    show_o2 = not (can_auto_breathe and model.player.o2 >= O2_MAX)
    if show_o2:
        o2_frac = model.player.o2 / O2_MAX
        # Background
        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 0)
        # Fill — color based on level
        fill_color = 11 if o2_frac > 0.5 else (9 if o2_frac > 0.25 else 8)
        pyxel.rect(bar_x, bar_y, int(bar_w * o2_frac), bar_h, fill_color)
        # Label
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
    tile_names = {
        SAND: "sand",
        SAND_DARK: "dark_sand",
        CLIFF: "cliff",
        CLIFF_EDGE: "cliff_edge",
        PALM_TREE: "palm",
        CACTUS: "cactus",
        DEAD_BUSH: "dead_bush",
        ROCK: "rock",
        WATER: "water",
        WATER_DEEP: "deep_water",
        BUSH_GREEN: "bush_green",
        BUSH_RED: "bush_red",
        BUSH_YELLOW: "bush_yellow",
    }
    map_bottom = VIEWPORT_H * TILE_SIZE
    pyxel.rect(0, map_bottom, SCREEN_W, DEBUG_HEIGHT, 0)
    dir_name = {UP: "UP", DOWN: "DOWN", LEFT: "LEFT", RIGHT: "RIGHT"}
    tile_name = {
        GRASS: "grass",
        TALL_GRASS: "tall_grass",
        FLOWERS: "flowers",
        DIRT: "dirt",
        WATER: "water",
        SAND: "sand",
        TREE: "tree",
        ROCK: "rock",
        BUSH: "bush",
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
        pyxel.text(2, y, line, 7)
        y += pyxel.FONT_HEIGHT + 2


# ---------------------------------------------------------------------------
# Dark Pocket World view
# ---------------------------------------------------------------------------

_BOSS_SPRITE_KEYS = {
    "head": "head",
    "wings": "wings",
    "arms_left": "arms",
    "arms_right": "arms",
}


def _blt_dark_sprite(sx: int, sy: int, key: str, w: int, h: int):
    """Draw a sprite using DARK_SPRITE_MAP, with transparency color 0."""
    info = DARK_SPRITE_MAP.get(key)
    if info:
        bank, u, v, sw, sh = info
        pyxel.blt(sx, sy, bank, u, v, w, h, 0)


def view_dark_play(model: Model):
    global _minimap_cache_seed
    _minimap_cache_seed = None  # bank 2 is now used for dark sprites
    pyxel.cls(0)
    dw = model.dark_world
    if dw is None:
        return

    px, py = model.player.pos
    cam_x = px - VIEWPORT_W // 2
    cam_y = py - VIEWPORT_H // 2

    # Draw normal map tiles using dark sprites (bank 2 instead of bank 1)
    tilemap = model.map.tilemap
    for sy in range(VIEWPORT_H):
        for sx in range(VIEWPORT_W):
            tx = cam_x + sx
            ty = cam_y + sy
            if tx < 0 or tx >= MAP_W or ty < 0 or ty >= MAP_H:
                pyxel.rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 0)
                continue
            tile = tilemap[ty][tx]
            draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.game.frame, bank=2)

    # Draw boss parts with layering: back → front
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
        if name == "wings":
            bank, su, sv, sw, sh = DARK_SPRITE_MAP["wings"]
            half_w = sw // 2
            pyxel.blt(bx, by, bank, su, sv, half_w, sh, 0)
            pyxel.blt(bx + bw - half_w, by, bank, su + half_w, sv, half_w, sh, 0)
        else:
            sprite_key = _BOSS_SPRITE_KEYS.get(part.name)
            if sprite_key and sprite_key in DARK_SPRITE_MAP:
                bank, su, sv, sw, sh = DARK_SPRITE_MAP[sprite_key]
                draw_w = -sw if part.name == "arms_right" else sw
                pyxel.blt(bx, by, bank, su, sv, draw_w, sh, 0)

    # Draw projectiles
    for proj in dw.projectiles:
        proj_sx = (proj.pos.x - cam_x) * TILE_SIZE
        proj_sy = (proj.pos.y - cam_y) * TILE_SIZE
        pkey = "projectile_1" if (model.game.frame // 6) % 2 == 0 else "projectile_2"
        bank, su, sv, sw, sh = DARK_SPRITE_MAP[pkey]
        pyxel.blt(proj_sx, proj_sy, bank, su, sv, sw, sh, 0)

    # Draw minions
    for m in dw.minions:
        if m.hp <= 0:
            continue
        mx = (m.pos.x - cam_x) * TILE_SIZE
        my = (m.pos.y - cam_y) * TILE_SIZE
        if m.kind in DARK_SPRITE_MAP:
            bank, su, sv, sw, sh = DARK_SPRITE_MAP[m.kind]
            draw_w = -sw if m.facing.x >= 0 else sw
            pyxel.blt(mx, my, bank, su, sv, draw_w, sh, 0)

    # Draw wizard companion when present.
    if dw.wizard_pos is not None:
        wise = dw.wizard_pos
        wise_sx = (wise.x - cam_x) * TILE_SIZE + (TILE_SIZE - 16) // 2
        wise_sy = (wise.y - cam_y) * TILE_SIZE
        if px < wise.x:
            wise_facing = LEFT
        elif px > wise.x:
            wise_facing = RIGHT
        else:
            wise_facing = DOWN
        draw_wise_man(wise_sx, wise_sy, wise_facing)

    # Friendly wizard projectiles.
    for shot in dw.wizard_shots:
        shot_sx = int((shot.x - cam_x) * TILE_SIZE)
        shot_sy = int((shot.y - cam_y) * TILE_SIZE)
        if 0 <= shot_sx < SCREEN_W and 0 <= shot_sy < VIEWPORT_H * TILE_SIZE:
            pyxel.pset(shot_sx, shot_sy, 12)
            pyxel.pset(shot_sx + 1, shot_sy, 7)

    # Draw player
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    if model.player.invincible_timer > 0 and (model.game.frame // 4) % 2 == 0:
        pass  # blink — don't draw
    else:
        draw_character(pcx, pcy, model.player.facing, model.game.frame)

    # Punch visual
    if model.player.punch_timer > PUNCH_COOLDOWN - 4:
        f = model.player.facing
        for i in range(1, 3):
            flash_x = pcx + f.x * i * TILE_SIZE + TILE_SIZE // 2
            flash_y = pcy + f.y * i * TILE_SIZE + TILE_SIZE // 2
            pyxel.circ(flash_x, flash_y, 6, 10)
            pyxel.circ(flash_x, flash_y, 3, 7)

    # HUD: Player HP
    hud_y = 6
    hud_font = _get_hud_font()
    for i in range(PLAYER_MAX_HP):
        hx = 8 + i * 18
        col = 8 if i < model.player.hp else 1
        pyxel.rect(hx, hud_y, 14, 14, col)
        pyxel.rectb(hx, hud_y, 14, 14, 7)

    # Boss status
    alive_count = sum(1 for p in dw.boss.parts if p.hp > 0)
    total_count = len(dw.boss.parts)
    status = f"Boss: {alive_count}/{total_count} parts"
    if hud_font:
        pyxel.text(SCREEN_W - hud_font.text_width(status) - 8, hud_y + 2, status, 7, hud_font)
    else:
        pyxel.text(SCREEN_W - len(status) * pyxel.FONT_WIDTH - 8, hud_y + 2, status, 7)

    # Controls hint at bottom
    map_bottom = VIEWPORT_H * TILE_SIZE
    pyxel.rect(0, map_bottom, SCREEN_W, DEBUG_HEIGHT, 0)
    pyxel.text(2, map_bottom + 2, f"HP:{model.player.hp}/{PLAYER_MAX_HP}  [F] Punch  [WASD/Arrows] Move", 7)
    pyxel.text(2, map_bottom + 12, f"Boss parts alive: {alive_count}/{total_count}  Minions: {len([m for m in dw.minions if m.hp > 0])}", 7)


def view_ending_b(model: Model):
    pyxel.cls(0)
    ui_font = _get_ui_font()
    title_font = _get_title_font()

    _center_text(140, "YOU SAVED THE", 7, title_font)
    _center_text(190, "POCKET WORLD", 11, title_font)

    _center_text(260, "The dark pocket world has been defeated.", 13, ui_font)
    _center_text(290, "The stolen land returns to its rightful place.", 13, ui_font)
    _center_text(320, "Peace is restored.", 7, ui_font)

    _center_text(380, "-- ENDING B --", 14, ui_font)

    blink = (model.game.frame // 30) % 2 == 0
    if blink:
        _center_text(430, "[ENTER] Return to Title", 7, ui_font)
