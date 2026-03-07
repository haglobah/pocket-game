"""Generate pocket_world.pyxres — renders all tile and character sprites to image bank 0."""

import pyxel

# Tile size
TILE_SIZE = 32

# Tile colors (pyxel palette indices)
GRASS = 0
TALL_GRASS = 1
FLOWERS = 2
DIRT = 3
WATER = 4
SAND = 5
TREE = 6
ROCK = 7
BUSH = 8

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

# Character sprite colors
COL_BODY = 10
COL_EYE = 0
COL_FEET = 4
COL_BELLY = 9

# Directions
from collections import namedtuple
Point = namedtuple("Point", ["x", "y"])
UP = Point(0, -1)
DOWN = Point(0, 1)
LEFT = Point(-1, 0)
RIGHT = Point(1, 0)


def draw_tile_to_bank(ox: int, oy: int, tile: int, frame: int = 0):
    """Draw a tile at offset (ox, oy) on pyxel.images[0]."""
    img = pyxel.images[0]
    sx, sy = ox, oy
    col = TILE_COL[tile]

    # Fill background
    for dy in range(TILE_SIZE):
        for dx in range(TILE_SIZE):
            img.pset(sx + dx, sy + dy, col)

    match tile:
        case t if t == GRASS:
            for pos in [(5, 7), (19, 4), (12, 17), (26, 23), (3, 25),
                        (22, 11), (8, 28), (28, 7), (15, 10), (6, 19)]:
                img.pset(sx + pos[0], sy + pos[1], 11)
            for bx, by in [(9, 13), (23, 19), (4, 22)]:
                for y in range(by, by + 4):
                    img.pset(sx + bx, sy + y, 11)
                img.pset(sx + bx, sy + by, 11)
                for y in range(by, by + 3):
                    img.pset(sx + bx + 1, sy + y, 3)
                img.pset(sx + bx + 1, sy + by, 3)

        case t if t == TALL_GRASS:
            for i in range(8):
                bx_ = 2 + i * 4
                h = 12 + (i % 4) * 2
                by_ = 30 - h
                # Main blade
                for y in range(by_, 31):
                    img.pset(sx + bx_, sy + y, 3)
                for y in range(by_ - 1, 31):
                    img.pset(sx + bx_ + 1, sy + y, 3)
                for y in range(by_ + 2, 31):
                    img.pset(sx + bx_ + 2, sy + y, 3)
                # Lighter tips
                for dy in range(2):
                    for dx in range(2):
                        img.pset(sx + bx_ + dx, sy + by_ - 1 + dy, 11)
                # Seed heads
                if i % 2 == 0:
                    for dy in range(2):
                        for dx in range(3):
                            img.pset(sx + bx_ - 1 + dx, sy + by_ - 3 + dy, 15)
                    img.pset(sx + bx_, sy + by_ - 4, 15)

        case t if t == FLOWERS:
            # Red flower
            for y in range(12, 25):
                img.pset(sx + 7, sy + y, 3)
            for dx in range(3):
                for dy in range(2):
                    img.pset(sx + 4 + dx, sy + 17 + dy, 11)
            for ddx, ddy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2)]:
                for dx in range(3):
                    for dy in range(3):
                        img.pset(sx + 6 + ddx + dx, sy + 10 + ddy + dy, 8)
            for dx in range(3):
                for dy in range(3):
                    img.pset(sx + 6 + dx, sy + 10 + dy, 10)

            # Yellow daisy
            for y in range(14, 27):
                img.pset(sx + 21, sy + y, 3)
            for dx in range(3):
                for dy in range(2):
                    img.pset(sx + 22 + dx, sy + 20 + dy, 11)
            for ddx, ddy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                for dx in range(3):
                    for dy in range(3):
                        img.pset(sx + 20 + ddx + dx, sy + 10 + ddy + dy, 10)
            for dx in range(3):
                for dy in range(3):
                    img.pset(sx + 20 + dx, sy + 10 + dy, 9)

            # Small purple flower
            for y in range(20, 29):
                img.pset(sx + 14, sy + y, 3)
            for dx in range(3):
                for dy in range(3):
                    img.pset(sx + 13 + dx, sy + 17 + dy, 14)
            img.pset(sx + 14, sy + 18, 7)

            # Tiny white wildflowers
            for px_, py_ in [(26, 24), (3, 27), (10, 28)]:
                for dx in range(2):
                    for dy in range(2):
                        img.pset(sx + px_ + dx, sy + py_ + dy, 7)

        case t if t == WATER:
            # Depth variation
            _img_rect(img, sx + 3, sy + 3, 8, 4, 1)
            _img_rect(img, sx + 18, sy + 14, 8, 4, 1)
            _img_rect(img, sx + 8, sy + 20, 6, 3, 1)
            # Medium depth
            _img_rect(img, sx + 12, sy + 6, 6, 3, 5)
            _img_rect(img, sx + 2, sy + 16, 5, 3, 5)
            # Animated ripple highlights
            offset = (frame // 10) % 32
            for ry, rlen in [(6, 5), (13, 4), (20, 6), (27, 3)]:
                rx = ((offset + ry * 3) % 26) + 3
                for dx in range(rlen):
                    img.pset(sx + rx + dx, sy + ry, 6)
            # Sparkle
            sparkle_x = (frame // 8 + 7) % 28 + 2
            sparkle_y = (frame // 12 + 13) % 28 + 2
            img.pset(sx + sparkle_x, sy + sparkle_y, 7)

        case t if t == SAND:
            # Ripple lines
            for ry in [8, 16, 24]:
                for dx in range(28):
                    img.pset(sx + 2 + dx, sy + ry, 10)
            # Pebbles
            for px_, py_ in [(7, 5), (22, 18), (5, 22), (18, 4), (27, 27)]:
                for dx in range(2):
                    for dy in range(2):
                        img.pset(sx + px_ + dx, sy + py_ + dy, 10)
            # Shell
            _img_rect(img, sx + 12, sy + 13, 4, 3, 7)
            for dx in range(2):
                img.pset(sx + 13 + dx, sy + 12, 7)
            img.pset(sx + 13, sy + 14, 6)
            for dx in range(4):
                img.pset(sx + 12 + dx, sy + 15, 10)
            # Darker sand patches
            _img_rect(img, sx + 3, sy + 10, 3, 2, 10)
            _img_rect(img, sx + 24, sy + 8, 3, 2, 10)

        case t if t == TREE:
            # Ground shadow
            _img_rect(img, sx + 6, sy + 28, 20, 3, 11)
            _img_rect(img, sx + 10, sy + 27, 12, 1, 11)
            # Roots
            _img_line(img, sx + 10, sy + 28, sx + 7, sy + 30, 4)
            _img_line(img, sx + 22, sy + 28, sx + 25, sy + 30, 4)
            _img_line(img, sx + 14, sy + 29, sx + 13, sy + 31, 4)
            # Trunk
            _img_rect(img, sx + 12, sy + 17, 8, 12, 4)
            # Bark texture
            _img_rect(img, sx + 14, sy + 18, 3, 10, 2)
            img.pset(sx + 13, sy + 20, 2)
            img.pset(sx + 18, sy + 22, 2)
            _img_line(img, sx + 13, sy + 24, sx + 15, sy + 26, 2)
            # Canopy — back layer
            _img_circ(img, sx + 16, sy + 10, 14, 11)
            # Canopy — mid layer
            _img_circ(img, sx + 12, sy + 8, 8, 3)
            _img_circ(img, sx + 21, sy + 9, 7, 3)
            _img_circ(img, sx + 16, sy + 12, 7, 3)
            # Canopy — highlights
            _img_circ(img, sx + 14, sy + 6, 5, 11)
            _img_circ(img, sx + 20, sy + 7, 4, 11)
            _img_circ(img, sx + 16, sy + 4, 3, 3)
            # Light spots
            _img_rect(img, sx + 10, sy + 5, 2, 2, 11)
            _img_rect(img, sx + 22, sy + 4, 2, 2, 11)
            img.pset(sx + 16, sy + 2, 3)

        case t if t == ROCK:
            # Ground shadow
            _img_rect(img, sx + 3, sy + 26, 26, 3, 1)
            # Main body
            _img_rect(img, sx + 4, sy + 8, 24, 18, 13)
            _img_rect(img, sx + 6, sy + 5, 20, 3, 13)
            _img_rect(img, sx + 9, sy + 3, 14, 2, 13)
            # Highlight
            _img_rect(img, sx + 7, sy + 6, 8, 4, 5)
            _img_rect(img, sx + 9, sy + 4, 6, 2, 5)
            _img_rect(img, sx + 8, sy + 10, 4, 3, 5)
            # Shadow
            _img_rect(img, sx + 18, sy + 20, 8, 5, 1)
            _img_rect(img, sx + 24, sy + 14, 3, 6, 1)
            _img_rect(img, sx + 22, sy + 18, 2, 4, 1)
            # Cracks
            _img_line(img, sx + 14, sy + 8, sx + 16, sy + 14, 1)
            _img_line(img, sx + 16, sy + 14, sx + 18, sy + 16, 1)
            _img_line(img, sx + 16, sy + 14, sx + 14, sy + 18, 1)
            # Moss
            _img_rect(img, sx + 5, sy + 20, 3, 2, 3)
            _img_rect(img, sx + 10, sy + 23, 4, 2, 3)
            img.pset(sx + 7, sy + 22, 11)

        case t if t == BUSH:
            # Ground shadow
            _img_rect(img, sx + 6, sy + 27, 20, 3, 11)
            _img_rect(img, sx + 10, sy + 26, 12, 1, 11)
            # Stem
            _img_rect(img, sx + 14, sy + 24, 4, 4, 4)
            # Main foliage
            _img_circ(img, sx + 16, sy + 16, 12, 11)
            # Mid clusters
            _img_circ(img, sx + 10, sy + 14, 7, 3)
            _img_circ(img, sx + 22, sy + 16, 7, 3)
            _img_circ(img, sx + 16, sy + 12, 6, 3)
            # Highlights
            _img_circ(img, sx + 12, sy + 11, 4, 11)
            _img_circ(img, sx + 20, sy + 13, 4, 11)
            _img_circ(img, sx + 16, sy + 10, 3, 3)
            # Leaf detail
            _img_rect(img, sx + 6, sy + 10, 2, 2, 11)
            _img_rect(img, sx + 24, sy + 12, 2, 2, 11)
            # Berries
            _img_rect(img, sx + 11, sy + 18, 3, 3, 8)
            img.pset(sx + 12, sy + 18, 14)
            _img_rect(img, sx + 19, sy + 14, 3, 3, 8)
            img.pset(sx + 20, sy + 14, 14)
            _img_rect(img, sx + 14, sy + 20, 2, 2, 8)
            _img_rect(img, sx + 23, sy + 20, 2, 2, 8)

        case t if t == DIRT:
            # Color variation
            _img_rect(img, sx + 5, sy + 8, 5, 4, 2)
            _img_rect(img, sx + 18, sy + 4, 6, 3, 2)
            _img_rect(img, sx + 10, sy + 22, 5, 3, 2)
            _img_rect(img, sx + 24, sy + 18, 4, 4, 2)
            # Pebbles
            _img_rect(img, sx + 13, sy + 12, 3, 2, 5)
            _img_rect(img, sx + 22, sy + 10, 2, 2, 5)
            _img_rect(img, sx + 6, sy + 26, 3, 2, 5)
            _img_rect(img, sx + 26, sy + 25, 2, 2, 5)
            # Dots
            for px_, py_ in [(3, 14), (8, 5), (20, 27), (28, 8), (15, 28), (2, 20)]:
                img.pset(sx + px_, sy + py_, 2)
            # Crack
            _img_line(img, sx + 16, sy + 16, sx + 20, sy + 19, 2)
            img.pset(sx + 20, sy + 20, 2)


def draw_character_to_bank(ox: int, oy: int, facing: Point, walk_bob: int):
    """Draw character sprite at offset (ox, oy) on pyxel.images[0]."""
    img = pyxel.images[0]
    sx, sy = ox, oy

    # Fill with transparent color (2)
    for dy in range(TILE_SIZE):
        for dx in range(TILE_SIZE):
            img.pset(sx + dx, sy + dy, 2)

    # Shadow
    _img_rect(img, sx + 8, sy + 29, 16, 3, 1)
    _img_rect(img, sx + 12, sy + 28, 8, 1, 1)

    # Body
    _img_rect(img, sx + 6, sy + 4, 20, 20, COL_BODY)
    _img_rect(img, sx + 8, sy + 2, 16, 24, COL_BODY)
    _img_rect(img, sx + 10, sy + 1, 12, 26, COL_BODY)

    # Belly
    _img_rect(img, sx + 10, sy + 12, 12, 8, COL_BELLY)
    _img_rect(img, sx + 12, sy + 10, 8, 12, COL_BELLY)
    _img_rect(img, sx + 11, sy + 11, 10, 10, COL_BELLY)

    # Ears
    _img_rect(img, sx + 7, sy, 4, 4, COL_BODY)
    _img_rect(img, sx + 21, sy, 4, 4, COL_BODY)
    _img_rect(img, sx + 8, sy + 1, 2, 2, COL_BELLY)
    _img_rect(img, sx + 22, sy + 1, 2, 2, COL_BELLY)

    # Face based on direction
    match facing:
        case Point(0, -1):  # up
            _img_rect(img, sx + 9, sy + 5, 4, 3, COL_BELLY)
            _img_rect(img, sx + 19, sy + 5, 4, 3, COL_BELLY)
            _img_rect(img, sx + 14, sy + 25, 4, 4, COL_BELLY)
            _img_rect(img, sx + 15, sy + 27, 2, 3, COL_BELLY)
        case Point(0, 1):  # down
            _img_rect(img, sx + 8, sy + 6, 6, 6, 7)
            _img_rect(img, sx + 18, sy + 6, 6, 6, 7)
            _img_rect(img, sx + 10, sy + 8, 4, 4, COL_EYE)
            _img_rect(img, sx + 20, sy + 8, 4, 4, COL_EYE)
            _img_rect(img, sx + 11, sy + 8, 2, 2, 7)
            _img_rect(img, sx + 21, sy + 8, 2, 2, 7)
            _img_rect(img, sx + 14, sy + 14, 4, 2, 4)
            _img_line(img, sx + 13, sy + 18, sx + 16, sy + 19, COL_EYE)
            _img_line(img, sx + 16, sy + 19, sx + 19, sy + 18, COL_EYE)
            _img_rect(img, sx + 6, sy + 13, 3, 2, 8)
            _img_rect(img, sx + 23, sy + 13, 3, 2, 8)
        case Point(-1, 0):  # left
            _img_rect(img, sx + 6, sy + 6, 6, 6, 7)
            _img_rect(img, sx + 6, sy + 8, 4, 4, COL_EYE)
            _img_rect(img, sx + 7, sy + 8, 2, 2, 7)
            _img_rect(img, sx + 4, sy + 13, 3, 2, 4)
            _img_line(img, sx + 5, sy + 17, sx + 8, sy + 18, COL_EYE)
            _img_rect(img, sx + 6, sy + 14, 2, 2, 8)
            _img_rect(img, sx + 24, sy + 16, 4, 4, COL_BELLY)
            _img_rect(img, sx + 26, sy + 14, 3, 3, COL_BELLY)
        case Point(1, 0):  # right
            _img_rect(img, sx + 20, sy + 6, 6, 6, 7)
            _img_rect(img, sx + 22, sy + 8, 4, 4, COL_EYE)
            _img_rect(img, sx + 23, sy + 8, 2, 2, 7)
            _img_rect(img, sx + 25, sy + 13, 3, 2, 4)
            _img_line(img, sx + 24, sy + 17, sx + 27, sy + 18, COL_EYE)
            _img_rect(img, sx + 24, sy + 14, 2, 2, 8)
            _img_rect(img, sx + 4, sy + 16, 4, 4, COL_BELLY)
            _img_rect(img, sx + 3, sy + 14, 3, 3, COL_BELLY)

    # Arms
    if walk_bob:
        _img_rect(img, sx + 4, sy + 12, 3, 6, COL_BODY)
        _img_rect(img, sx + 25, sy + 10, 3, 6, COL_BODY)
        _img_rect(img, sx + 4, sy + 17, 2, 2, COL_BODY)
        _img_rect(img, sx + 26, sy + 15, 2, 2, COL_BODY)
    else:
        _img_rect(img, sx + 4, sy + 10, 3, 6, COL_BODY)
        _img_rect(img, sx + 25, sy + 12, 3, 6, COL_BODY)
        _img_rect(img, sx + 4, sy + 15, 2, 2, COL_BODY)
        _img_rect(img, sx + 26, sy + 17, 2, 2, COL_BODY)

    # Feet
    if walk_bob:
        _img_rect(img, sx + 8, sy + 26, 5, 4, COL_FEET)
        _img_rect(img, sx + 19, sy + 24, 5, 4, COL_FEET)
    else:
        _img_rect(img, sx + 8, sy + 24, 5, 4, COL_FEET)
        _img_rect(img, sx + 19, sy + 26, 5, 4, COL_FEET)


# --- Helper functions for drawing on image bank ---

def _img_rect(img, x, y, w, h, col):
    for dy in range(h):
        for dx in range(w):
            img.pset(x + dx, y + dy, col)


def _img_line(img, x0, y0, x1, y1, col):
    """Bresenham's line algorithm on image bank."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx_ = 1 if x0 < x1 else -1
    sy_ = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        img.pset(x0, y0, col)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx_
        if e2 < dx:
            err += dx
            y0 += sy_


def _img_circ(img, cx, cy, r, col):
    """Filled circle on image bank."""
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                img.pset(cx + dx, cy + dy, col)


def main():
    pyxel.init(256, 256, display_scale=1)

    # Row 0: static tiles (GRASS through ROCK)
    for tile_id in range(8):  # GRASS=0 .. ROCK=7
        draw_tile_to_bank(tile_id * 32, 0, tile_id)

    # Row 1, x=0: BUSH
    draw_tile_to_bank(0, 32, BUSH)

    # Water animation frames at specific frame values
    # Frame 0 is already at (128, 0) from the static tiles row
    # Frames 1-3 at row 1: (32, 32), (64, 32), (96, 32)
    water_frames = [80, 160, 240]
    for i, frame_val in enumerate(water_frames):
        draw_tile_to_bank(32 * (i + 1), 32, WATER, frame=frame_val)

    # Row 2: Character sprites (4 directions x 2 walk frames)
    directions = [DOWN, UP, LEFT, RIGHT]
    for dir_idx, facing in enumerate(directions):
        for walk_bob in range(2):
            x = (dir_idx * 2 + walk_bob) * 32
            draw_character_to_bank(x, 64, facing, walk_bob)

    pyxel.save("pocket_world.pyxres")
    print("Saved pocket_world.pyxres")
    pyxel.quit()


main()
