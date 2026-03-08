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
)


@dataclass(frozen=True)
class ThoughtBubble:
    memory_id: str
    text: str
    timer: int
    duration: int


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


@dataclass(frozen=True)
class PlantObject:
    anchor: Point       # map position (blocks movement)
    kind: str           # "palm_tree" | "cactus" | "bush_berry"
    has_fruit: bool     # True = edible, False = already eaten


@dataclass(frozen=True)
class Map:
    tilemap: tuple[tuple[int, ...], ...]
    seed: int
    objects: tuple[PlantObject, ...]

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
    state: str  # "title" | "play" | "dead" | "rewind"
    seed_input: str
    frame: int
    thought: ThoughtBubble | None
    seen_memories: tuple[str, ...]
    thought_cooldown: int
    show_minimap: bool


@dataclass(frozen=True)
class Model:
    player: Player
    map: Map
    cycle: Cycle
    game: Game


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
        ),
        map=Map(
            tilemap=(),
            seed=0,
            objects=(),
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
