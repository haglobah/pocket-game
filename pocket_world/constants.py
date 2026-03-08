from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])

MAP_W = 2000
MAP_H = 1000
TILE_SIZE = 32
VIEWPORT_W = 24  # tiles visible on screen
VIEWPORT_H = 24
DEBUG_HEIGHT = 60
SCREEN_W = VIEWPORT_W * TILE_SIZE  # 512
SCREEN_H = VIEWPORT_H * TILE_SIZE + DEBUG_HEIGHT

# Tile types
SAND = 0
SAND_DARK = 1
CLIFF = 2
CLIFF_EDGE = 3
PALM_TREE = 4
CACTUS = 5
DEAD_BUSH = 6
ROCK = 7
WATER = 8
WATER_DEEP = 9
BUSH_GREEN = 10
BUSH_FLOWERING = 11
BUSH_BERRY = 12

# Keep old names mapped for compatibility
GRASS = SAND
TALL_GRASS = SAND
FLOWERS = SAND
DIRT = SAND_DARK
TREE = PALM_TREE
BUSH = DEAD_BUSH


def is_walkable(tile: int) -> bool:
    return tile in (SAND, SAND_DARK, DEAD_BUSH, BUSH_GREEN, BUSH_FLOWERING, BUSH_BERRY)


def is_swimmable(tile: int) -> bool:
    return tile in (WATER, WATER_DEEP)


# Movement speed (frames between steps)
MOVE_DELAY_WATER = 12
MOVE_DELAY_LAND = 8
MOVE_DELAY_RUNNING = 4

# O2 system
O2_MAX = 20 * 60  # 40 seconds at 60fps
O2_BREATHE_REFILL = 10 * 60  # 20 seconds refill per key press
O2_AUTO_REFILL_RATE = 4  # frames of O2 restored per frame when auto-breathing
O2_LUNGS_UNDERWATER_CHUNK = 3 * 60  # 3 seconds of O2 lost per gulp (every second)

# Hydration system
HYDRATION_MAX = 5 * 60 * 60  # 5 min at 60fps
HYDRATION_START = 1 * 60 * 60 # 1 min at 60fps
HYDRATION_REFILL = 1 * 60 * 60  # 1 min per gulp
HYDRATION_DEPLETION = 1  # frames lost per frame

# Hunger system
HUNGER_MAX = 10 * 60 * 60  # 10 min at 60fps
HUNGER_START = 3 * 60 * 60  # 10 min at 60fps
HUNGER_REFILL = 5 * 60 * 60  # 5 min per eat
HUNGER_DEPLETION = 1  # frames lost per frame

# Edible / drinkable tiles
FOOD_TILES = (4, 5, 12)  # PALM_TREE, CACTUS, BUSH_BERRY
DRINK_TILES = (8, 9)  # WATER, WATER_DEEP

# Death screen / rewind
DEATH_SCREEN_MIN_FRAMES = 60  # minimum frames before ENTER accepted
REWIND_DURATION = 180  # 3 seconds at 60fps

# Breathing modes
LUNGS = "lungs"
GILLS = "gills"

# Thought bubbles
THOUGHT_CHAR_SPEED = 3  # frames per character (typing effect)
THOUGHT_READ_FRAMES = 180  # hold full text for 3 seconds
THOUGHT_COOLDOWN_FRAMES = 600  # 10 seconds between thoughts
THOUGHT_INITIAL_DELAY = 180  # 3 seconds before first thought after spawn

# Wise-man idle dialogue bubbles
WISE_DIALOG_CHAR_SPEED = 2
WISE_DIALOG_READ_FRAMES = 210
WISE_DIALOG_COOLDOWN_FRAMES = 420
WISE_DIALOG_INITIAL_DELAY = 120
WISE_IDLE_LINES = (
    "Ah, another traveler waking in the dunes.",
    "Drink when you can. The sand is patient.",
    "Hold your breath for land. Let gills guide the deep.",
    "The world loops, but your learning stays.",
    "If you panic, count your breaths, then walk.",
    "Berries and cactus can buy you one more dawn.",
)
WISE_TALK_DISTANCE = 3
WISE_SPAWN_MIN_DISTANCE = 10
WISE_SPAWN_MAX_DISTANCE = 18
WISE_FOLLOW_STEP_FRAMES = 12
WISE_ATTACK_SHOT_SPEED = 3.0
WISE_ATTACK_SHOT_TTL = 240
WISE_ATTACK_COOLDOWN_FRAMES = 24
WISE_ATTACK_O2_DAMAGE = 300

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
