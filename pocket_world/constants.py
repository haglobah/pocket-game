from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])

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
O2_MAX = 20 * 60  # 40 seconds at 60fps
O2_BREATHE_REFILL = 10 * 60  # 20 seconds refill per key press
O2_AUTO_REFILL_RATE = 4  # frames of O2 restored per frame when auto-breathing
O2_LUNGS_UNDERWATER_CHUNK = 3 * 60  # 3 seconds of O2 lost per gulp (every second)

# Death screen / rewind
DEATH_SCREEN_MIN_FRAMES = 60  # minimum frames before ENTER accepted
REWIND_DURATION = 180  # 3 seconds at 60fps

# Breathing modes
LUNGS = "lungs"
GILLS = "gills"

# Thought bubbles
THOUGHT_CHAR_SPEED = 3       # frames per character (typing effect)
THOUGHT_READ_FRAMES = 180    # hold full text for 3 seconds
THOUGHT_COOLDOWN_FRAMES = 600  # 10 seconds between thoughts
THOUGHT_INITIAL_DELAY = 180  # 3 seconds before first thought after spawn

# Directions
UP = Point(0, -1)
DOWN = Point(0, 1)
LEFT = Point(-1, 0)
RIGHT = Point(1, 0)

# Diagonals
UP_LEFT = Point(-1, -1)
UP_RIGHT = Point(1, -1)
DOWN_LEFT = Point(-1, 1)
DOWN_RIGHT = Point(1, 1)

DIR_NAME = {
    UP: "UP",
    DOWN: "DOWN",
    LEFT: "LEFT",
    RIGHT: "RIGHT",
    UP_LEFT: "UP_LEFT",
    UP_RIGHT: "UP_RIGHT",
    DOWN_LEFT: "DOWN_LEFT",
    DOWN_RIGHT: "DOWN_RIGHT",
}
