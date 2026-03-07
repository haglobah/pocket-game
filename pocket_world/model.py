from dataclasses import dataclass
from .commands import Cmd
from .constants import (
    MAP_W,
    MAP_H,
    Point,
    O2_MAX,
    LUNGS,
    GILLS,
    DOWN,
    HYDRATION_MAX,
    HUNGER_MAX,
)


@dataclass(frozen=True)
class ThoughtBubble:
    memory_id: str
    text: str
    timer: int
    duration: int


@dataclass(frozen=True)
class Model:
    player_pos: Point
    facing: Point
    tilemap: tuple[tuple[int, ...], ...]
    seed: int
    move_timer: int  # counts down to 0 for continuous movement
    state: str  # "title" | "play" | "dead" | "rewind"
    seed_input: str  # text input on title screen
    frame: int  # animation frame counter
    o2: int  # O2 in frames remaining (max O2_MAX)
    breathing_mode: str  # LUNGS or GILLS
    hydration: int  # hydration in frames remaining (max HYDRATION_MAX)
    hunger: int  # hunger in frames remaining (max HUNGER_MAX)
    cycle: int  # current cycle number (starts at 1)
    death_reason: str  # reason of death for death screen
    learned: tuple[str, ...]  # skills learned this cycle
    death_timer: int  # frames spent on death screen
    rewind_timer: int  # frames remaining in rewind animation
    thought: ThoughtBubble | None
    seen_memories: tuple[str, ...]
    thought_cooldown: int
    show_minimap: bool  # whether minimap overlay is visible


def init() -> tuple[Model, list[Cmd]]:
    model = Model(
        player_pos=Point(MAP_W // 2, MAP_H // 2),
        facing=DOWN,
        tilemap=(),
        seed=0,
        move_timer=0,
        state="title",
        seed_input="",
        frame=0,
        o2=O2_MAX,
        breathing_mode=LUNGS,
        hydration=HYDRATION_MAX,
        hunger=HUNGER_MAX,
        cycle=1,
        death_reason="",
        learned=(),
        death_timer=0,
        rewind_timer=0,
        thought=None,
        seen_memories=(),
        thought_cooldown=0,
        show_minimap=False,
    )
    return model, []
