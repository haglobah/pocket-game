from dataclasses import dataclass

from .constants import Point


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
    hunger: int  # hunger in frames remaining (max HUNGER_MAX)
    breathing_mode: str  # LUNGS or GILLS
    cycle: int  # current cycle number (starts at 1)
    death_reason: str  # reason of death for death screen
    learned: tuple[str, ...]  # skills learned this cycle
    death_timer: int  # frames spent on death screen
    rewind_timer: int  # frames remaining in rewind animation
    thought: ThoughtBubble | None
    seen_memories: tuple[str, ...]
    thought_cooldown: int
