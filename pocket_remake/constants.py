"""Dimensions, tile types, tuning values and the Point type."""

from typing import NamedTuple


class Point(NamedTuple):
    x: int
    y: int


# Screen
WIDTH = 512
HEIGHT = 512
FPS = 60
TILE = 16  # 8x8 pixel art drawn at 2x
VIEW_TILES = 32

# World
MAP_W = 2000
MAP_H = 1000
CHUNK = 8  # explored-area granularity, in tiles

# Tiles
SAND = 0
DARK_SAND = 1
CLIFF = 2
CLIFF_EDGE = 3
PALM = 4
CACTUS = 5
DEAD_BUSH = 6
ROCK = 7
WATER = 8
DEEP_WATER = 9
GREEN_BUSH = 10
RED_BUSH = 11
YELLOW_BUSH = 12
PORTAL = 13
DARK_FLOOR = 14
DARK_WALL = 15
WRECK = 16

WALKABLE = frozenset(
    {SAND, DARK_SAND, DEAD_BUSH, GREEN_BUSH, RED_BUSH, YELLOW_BUSH, PORTAL, DARK_FLOOR}
)
SWIMMABLE = frozenset({WATER, DEEP_WATER})
PLANTS = frozenset({PALM, CACTUS})

# Layout
SPAWN_CLEAR = 75  # no plants, rocks or bushes this close to spawn
OASIS_RING = (85, 110)
OASIS_SPACING = 50
PORTAL_RING = (150, 175)
WIZARD_RING = (10, 18)

# Movement (frames per step)
STEP_LAND = 8
STEP_SPRINT = 4
STEP_WATER = 12

# Breathing
O2_MAX = 1200  # 20 s
LUNG_REFILL = 4  # per frame, lungs on land
DROWN_LOSS = 180  # per second, lungs underwater
GILL_DRAIN = 1  # per frame, gills anywhere
BREATHE_GAIN = 600  # per Space press, gills underwater

# Needs
MINUTE = 60 * FPS
WATER_MAX = 5 * MINUTE
WATER_START = 1 * MINUTE
DRINK_GAIN = 1 * MINUTE
FOOD_MAX = 10 * MINUTE
FOOD_START = 3 * MINUTE
EAT_GAIN = 5 * MINUTE
POISON_FRAMES = 10 * FPS
POISON_DRAIN = 6  # O2 per frame

# Thoughts
THOUGHT_CHAR_FRAMES = 3
THOUGHT_HOLD = 3 * FPS
THOUGHT_COOLDOWN = 10 * FPS
THOUGHT_FIRST = 3 * FPS

# Wizard
WIZARD_IDLE_START = 5 * FPS
WIZARD_IDLE_EVERY = 6 * FPS
WIZARD_LINE_HOLD = 4 * FPS
WIZARD_TALK_RANGE = 3
WIZARD_LISTEN_RANGE = 6
WIZARD_FOLLOW_EVERY = 12
WIZARD_BOLT_EVERY = 24
WIZARD_BOLT_RANGE = 14
WIZARD_BOLT_SPEED = 0.25  # tiles per frame
BOLT_DAMAGE = 300
COMPANION_RANGE = 18
COMPANION_EVERY = 20

# Screens
DEATH_CONFIRM_DELAY = 60
REWIND_FRAMES = 180

# Dark world
DARK_HP = 5
DARK_IFRAMES = 60
PUNCH_RANGE = 2
PUNCH_COOLDOWN = 20
BOSS_FIRE_EVERY = 96
BOSS_SHOT_SPEED = 0.2  # one tile per 5 frames
SEED_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"
SEED_MAX = 16
