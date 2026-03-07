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


@dataclass(frozen=True)
class Breathe(Msg):
    pass


@dataclass(frozen=True)
class ToggleBreathingMode(Msg):
    pass


@dataclass(frozen=True)
class EatPlant(Msg):
    pass


@dataclass(frozen=True)
class Die(Msg):
    reason: str


@dataclass(frozen=True)
class DismissDeathScreen(Msg):
    pass


@dataclass(frozen=True)
class RewindTick(Msg):
    pass
