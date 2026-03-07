import pyxel

from .constants import (
    SCREEN_W, SCREEN_H, TILE_SIZE, VIEWPORT_W, VIEWPORT_H, DEBUG_HEIGHT,
    MAP_W, MAP_H,
    WATER, GRASS, TALL_GRASS, FLOWERS, DIRT, SAND, TREE, ROCK, BUSH,
    UP, DOWN, LEFT, RIGHT,
    LUNGS, O2_MAX, DEATH_SCREEN_MIN_FRAMES, REWIND_DURATION,
    THOUGHT_CHAR_SPEED,
)
from .model import Model, ThoughtBubble


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


def draw_character(sx: int, sy: int, facing, frame: int):
    """Draw a creature sprite at screen pixel position (32x32), using sprites."""
    walk_bob = (frame // 6) % 2
    dir_idx = {DOWN: 0, UP: 1, LEFT: 2, RIGHT: 3}[facing]
    u = (dir_idx * 2 + walk_bob) * 32
    pyxel.blt(sx, sy, 0, u, 64, 32, 32, 2)  # colkey=2 for transparency


def view(model: Model):
    if model.state == "title":
        view_title(model)
    elif model.state == "dead":
        view_death(model)
    elif model.state == "rewind":
        view_rewind(model)
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


def _center_text(y: int, text: str, col: int):
    """Draw text centered horizontally."""
    x = (SCREEN_W - len(text) * pyxel.FONT_WIDTH) // 2
    pyxel.text(x, y, text, col)


def view_death(model: Model):
    pyxel.cls(0)
    y = 120

    _center_text(y, f"Cycle {model.cycle} -- You died", 8)
    y += 30

    _center_text(y, f"Seed: {model.seed}", 13)
    y += 20

    _center_text(y, f"Reason: {model.death_reason}", 8)
    y += 40

    if model.learned:
        _center_text(y, "In this cycle, you learned:", 7)
        y += 16
        for skill in model.learned:
            _center_text(y, f"- {skill}", 11)
            y += 12
    else:
        _center_text(y, "You didn't learn anything this cycle.", 13)
    y += 30

    if model.death_timer >= DEATH_SCREEN_MIN_FRAMES:
        blink = (model.death_timer // 30) % 2 == 0
        if blink:
            _center_text(y, "[ENTER] Continue", 7)


def _draw_hourglass(cx: int, cy: int, fill_frac: float):
    """Draw a simple hourglass at center (cx, cy). fill_frac 0..1 = how full bottom is."""
    # Outer frame
    hw, hh = 20, 40
    # Top triangle (emptying)
    top_fill = 1.0 - fill_frac
    # Bottom triangle (filling)
    for i in range(hh):
        # Width narrows toward middle
        if i < hh // 2:
            w = int(hw * (1 - i / (hh // 2)))
            # Top half: sand only in upper portion
            sand_h = int((hh // 2) * top_fill)
            col = 9 if i < sand_h else 0
        else:
            j = i - hh // 2
            w = int(hw * (j / (hh // 2)))
            # Bottom half: sand fills from bottom
            sand_h = int((hh // 2) * fill_frac)
            rows_from_bottom = hh - 1 - i
            col = 9 if rows_from_bottom < sand_h else 0
        if w > 0:
            pyxel.rect(cx - w, cy - hh // 2 + i, w * 2, 1, col)
    # Frame lines
    pyxel.line(cx - hw, cy - hh // 2, cx + hw, cy - hh // 2, 7)  # top
    pyxel.line(cx - hw, cy + hh // 2, cx + hw, cy + hh // 2, 7)  # bottom
    pyxel.line(cx - hw, cy - hh // 2, cx, cy, 7)  # top-left diagonal
    pyxel.line(cx + hw, cy - hh // 2, cx, cy, 7)  # top-right diagonal
    pyxel.line(cx - hw, cy + hh // 2, cx, cy, 7)  # bottom-left diagonal
    pyxel.line(cx + hw, cy + hh // 2, cx, cy, 7)  # bottom-right diagonal


def view_rewind(model: Model):
    pyxel.cls(0)
    # fill_frac goes from 0 to 1 as rewind_timer counts down
    fill_frac = 1.0 - (model.rewind_timer / REWIND_DURATION)

    _draw_hourglass(SCREEN_W // 2, SCREEN_H // 2 - 20, fill_frac)

    _center_text(SCREEN_H // 2 + 50, "Rewinding...", 7)

    # Cycle number
    _center_text(SCREEN_H // 2 + 70, f"Cycle {model.cycle + 1}", 13)


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


def _draw_thought_bubble(cx: int, bottom_y: int, thought: ThoughtBubble):
    """Draw a thought bubble centered at cx with tail ending at bottom_y."""
    chars_shown = min(len(thought.text), thought.timer // THOUGHT_CHAR_SPEED)
    display_text = thought.text[:chars_shown]
    if not display_text:
        return

    lines = _wrap_text(display_text, 28)
    fw = pyxel.FONT_WIDTH
    fh = pyxel.FONT_HEIGHT
    line_h = fh + 2

    text_w = max(len(line) for line in lines) * fw
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
        pyxel.text(lx, ty, line, 1)
        ty += line_h


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
                pyxel.rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE, 1)
            else:
                draw_tile(sx * TILE_SIZE, sy * TILE_SIZE, tile, model.frame)

    # Draw player at center of screen
    pcx = (VIEWPORT_W // 2) * TILE_SIZE
    pcy = (VIEWPORT_H // 2) * TILE_SIZE
    draw_character(pcx, pcy, model.facing, model.frame)

    # Thought bubble above player
    if model.thought is not None:
        player_cx = pcx + TILE_SIZE // 2
        player_top = pcy
        _draw_thought_bubble(player_cx, player_top - 6, model.thought)

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
