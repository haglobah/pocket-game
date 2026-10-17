"""Commands: side effects that update asks the shell to perform."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Cmd:
    pass


@dataclass(frozen=True)
class PlaySound(Cmd):
    sound: str


@dataclass(frozen=True)
class PlayMusic(Cmd):
    track: str


@dataclass(frozen=True)
class StopMusic(Cmd):
    pass


@dataclass(frozen=True)
class RandomSeedText(Cmd):
    """Roll a random seed text; answers with SeedChosen."""
