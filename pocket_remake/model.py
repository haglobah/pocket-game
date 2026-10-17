"""The game state. Everything is frozen; update returns new instances."""

from dataclasses import dataclass

from .constants import (
    DARK_HP,
    FOOD_START,
    O2_MAX,
    STEP_LAND,
    WATER_START,
    Point,
)
from .mapgen import World

ORIGIN = Point(0, 0)
DOWN = Point(0, 1)


@dataclass(frozen=True)
class Player:
    pos: Point = ORIGIN
    prev: Point = ORIGIN  # tile we are stepping from (for drawing)
    facing: Point = DOWN
    move_cd: int = 0  # frames until the current step completes
    move_len: int = STEP_LAND
    breath: str = "lungs"  # "lungs" | "gills"
    o2: int = O2_MAX
    water: int = WATER_START
    food: int = FOOD_START
    poison: int = 0  # frames of poison left
    underwater: int = 0  # frames spent underwater in a row


@dataclass(frozen=True)
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    ttl: int


@dataclass(frozen=True)
class Wizard:
    pos: Point
    prev: Point
    mode: str = "idle"  # "idle" | "talk" | "follow" | "attack"
    node: str = "opening"
    line: str = ""  # speech bubble text
    line_age: int = 0
    timer: int = 0
    idle_index: int = 0


@dataclass(frozen=True)
class Thought:
    id: str
    text: str
    age: int = 0


@dataclass(frozen=True)
class BossPart:
    name: str
    x: int
    y: int
    w: int
    h: int
    hp: int
    max_hp: int
    flash: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def contains(self, p: Point) -> bool:
        return self.x <= p.x < self.x + self.w and self.y <= p.y < self.y + self.h


@dataclass(frozen=True)
class Minion:
    kind: str
    pos: Point
    prev: Point
    hp: int
    move_cd: int
    flash: int = 0


@dataclass(frozen=True)
class Zap:
    """Companion lightning, drawn for a few frames."""

    x0: float
    y0: float
    x1: float
    y1: float
    age: int = 0


@dataclass(frozen=True)
class Dark:
    parts: tuple[BossPart, ...]
    minions: tuple[Minion, ...]
    hp: int = DARK_HP
    iframes: int = 0
    punch_cd: int = 0
    punch_anim: int = 0
    fire_cd: int = 96
    shots: tuple[Projectile, ...] = ()
    companion: Wizard | None = None
    zaps: tuple[Zap, ...] = ()


@dataclass(frozen=True)
class Model:
    state: str = "title"  # title | play | dead | rewind | dark_play | ending_b
    frame: int = 0
    state_timer: int = 0  # frames since the state was entered
    seed_text: str = ""
    seed: int = 0
    world: World | None = None
    cycle: int = 1
    player: Player = Player()
    learned: tuple[str, ...] = ()
    eaten: frozenset[Point] = frozenset()
    explored: frozenset[tuple[int, int]] = frozenset()  # persists across cycles
    seen: frozenset[str] = frozenset()  # memories already shown this game
    show_map: bool = True
    thought: Thought | None = None
    thought_cd: int = 0
    wizard: Wizard | None = None
    bolts: tuple[Projectile, ...] = ()
    death_reason: str = ""
    dark: Dark | None = None
