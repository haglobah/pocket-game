"""Messages: events that can change the model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Msg:
    pass


@dataclass(frozen=True)
class Tick(Msg):
    """One frame. Carries the held movement keys."""

    dx: int = 0
    dy: int = 0
    sprint: bool = False


@dataclass(frozen=True)
class TypeChar(Msg):
    char: str


@dataclass(frozen=True)
class Backspace(Msg):
    pass


@dataclass(frozen=True)
class Confirm(Msg):
    pass


@dataclass(frozen=True)
class SeedChosen(Msg):
    text: str


@dataclass(frozen=True)
class Breathe(Msg):
    pass


@dataclass(frozen=True)
class ToggleBreath(Msg):
    pass


@dataclass(frozen=True)
class Drink(Msg):
    pass


@dataclass(frozen=True)
class Eat(Msg):
    pass


@dataclass(frozen=True)
class ToggleMap(Msg):
    pass


@dataclass(frozen=True)
class Choose(Msg):
    option: int  # 1 or 2


@dataclass(frozen=True)
class Punch(Msg):
    pass
