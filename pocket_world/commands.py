from dataclasses import dataclass


@dataclass(frozen=True)
class Cmd:
    pass


@dataclass(frozen=True)
class GenerateMap(Cmd):
    seed: int


@dataclass(frozen=True)
class PlayStepSound(Cmd):
    pass


@dataclass(frozen=True)
class PlaySwimSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayThoughtSound(Cmd):
    pass
