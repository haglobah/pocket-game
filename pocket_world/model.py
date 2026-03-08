from dataclasses import dataclass

from pocket_world.commands import PlayTitleThemeMusic
from .constants import (
    MAP_W,
    MAP_H,
    Point,
    O2_MAX,
    LUNGS,
    GILLS,
    DOWN,
    HYDRATION_START,
    HUNGER_START,
    PLAYER_MAX_HP,
)


@dataclass(frozen=True)
class ThoughtBubble:
    memory_id: str
    text: str
    timer: int
    duration: int


@dataclass(frozen=True)
class NpcDialogueBubble:
    text: str
    timer: int
    duration: int


@dataclass(frozen=True)
class WizardShot:
    x: float
    y: float
    vx: float
    vy: float
    ttl: int


@dataclass(frozen=True)
class Player:
    pos: Point
    facing: Point
    move_timer: int
    sprinting: bool
    o2: int
    breathing_mode: str
    hydration: int
    hunger: int
    poison_timer: int
    hp: int = PLAYER_MAX_HP
    invincible_timer: int = 0
    punch_timer: int = 0


@dataclass(frozen=True)
class PlantObject:
    anchor: Point
    kind: str
    has_fruit: bool


@dataclass(frozen=True)
class Map:
    tilemap: tuple[tuple[int, ...], ...]
    seed: int
    wise_man: Point = Point(0, 0)
    objects: tuple[PlantObject, ...] = ()
    poison_water: frozenset = frozenset()

    def __post_init__(self):
        object.__setattr__(self, '_anchor_set', frozenset(obj.anchor for obj in self.objects))

    def has_object_at(self, pos: Point) -> bool:
        return pos in self._anchor_set


@dataclass(frozen=True)
class Cycle:
    number: int
    death_reason: str
    death_timer: int
    rewind_timer: int
    learned: tuple[str, ...]


@dataclass(frozen=True)
class Game:
    state: str  # "title" | "play" | "dead" | "rewind" | "dark_play" | "ending_b"
    seed_input: str
    frame: int
    thought: ThoughtBubble | None
    seen_memories: tuple[str, ...]
    thought_cooldown: int
    show_minimap: bool
    wise_dialogue: NpcDialogueBubble | None = None
    wise_options: tuple[str, str] | None = None
    wise_dialogue_active: bool = False
    wise_dialogue_node: str = ""
    wise_outcome: str = "none"  # "none" | "attack" | "follow"
    wise_dialogue_cooldown: int = 0
    wise_dialogue_index: int = 0
    wizard_shots: tuple[WizardShot, ...] = ()
    wizard_attack_cooldown: int = 0


@dataclass(frozen=True)
class BossPart:
    name: str
    hp: int
    max_hp: int
    pos: Point
    size: Point


@dataclass(frozen=True)
class Boss:
    parts: tuple[BossPart, ...]
    fire_timer: int
    phase: str  # "active" | "defeated"


@dataclass(frozen=True)
class Projectile:
    pos: Point
    velocity: Point
    alive: bool = True


@dataclass(frozen=True)
class Minion:
    kind: str
    pos: Point
    hp: int
    facing: Point
    move_timer: int


@dataclass(frozen=True)
class DarkWorld:
    boss: Boss
    minions: tuple[Minion, ...]
    projectiles: tuple[Projectile, ...]
    arena_tiles: tuple[tuple[int, ...], ...]
    tick: int = 0
    wizard_pos: Point | None = None
    wizard_shots: tuple[WizardShot, ...] = ()
    wizard_attack_cooldown: int = 0
    wizard_follow_timer: int = 0


@dataclass(frozen=True)
class Model:
    player: Player
    map: Map
    cycle: Cycle
    game: Game
    dark_world: DarkWorld | None = None


def init() -> tuple[Model, list]:
    model = Model(
        player=Player(
            pos=Point(MAP_W // 2, MAP_H // 2),
            facing=DOWN,
            move_timer=0,
            sprinting=False,
            o2=O2_MAX,
            breathing_mode=LUNGS,
            hydration=HYDRATION_START,
            hunger=HUNGER_START,
            poison_timer=0,
        ),
        map=Map(
            tilemap=(),
            seed=0,
        ),
        cycle=Cycle(
            number=1,
            death_reason="",
            death_timer=0,
            rewind_timer=0,
            learned=(),
        ),
        game=Game(
            state="title",
            seed_input="",
            frame=0,
            thought=None,
            seen_memories=(),
            thought_cooldown=0,
            show_minimap=False,
        ),
    )
    return model, [PlayTitleThemeMusic()]
