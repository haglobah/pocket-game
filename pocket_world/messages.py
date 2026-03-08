from dataclasses import dataclass

from .constants import Point


@dataclass(frozen=True)
class Msg:
    pass


@dataclass(frozen=True)
class Tick(Msg):
    pass


@dataclass(frozen=True)
class MoveDir(Msg):
    direction: Point


@dataclass(frozen=True)
class StartGame(Msg):
    seed: int


@dataclass(frozen=True)
class TypeChar(Msg):
    char: str


@dataclass(frozen=True)
class Backspace(Msg):
    pass


@dataclass(frozen=True)
class MapGenerated(Msg):
    tilemap: tuple[tuple[int, ...], ...]
    seed: int
    objects: tuple
    poison_water: frozenset


@dataclass(frozen=True)
class Breathe(Msg):
    pass


@dataclass(frozen=True)
class ToggleBreathingMode(Msg):
    pass


@dataclass(frozen=True)
class Drink(Msg):
    pass


@dataclass(frozen=True)
class Eat(Msg):
    pass


@dataclass(frozen=True)
class Die(Msg):
    reason: str


@dataclass(frozen=True)
class DismissDeathScreen(Msg):
    pass


@dataclass(frozen=True)
class ToggleMinimap(Msg):
    pass


@dataclass(frozen=True)
class RewindTick(Msg):
    pass


@dataclass(frozen=True)
class SetSprinting(Msg):
    active: bool


@dataclass(frozen=True)
class EnterDarkWorld(Msg):
    pass


@dataclass(frozen=True)
class Punch(Msg):
    pass


@dataclass(frozen=True)
class PlayerHit(Msg):
    damage: int


@dataclass(frozen=True)
class BossPartDestroyed(Msg):
    part_name: str


@dataclass(frozen=True)
class BossDefeated(Msg):
    pass


@dataclass(frozen=True)
class DarkWorldGenerated(Msg):
    boss_parts: tuple
    minions: tuple


@dataclass(frozen=True)
class DismissCredits(Msg):
    pass


@dataclass(frozen=True)
class ChooseWizardOption(Msg):
    option: int
