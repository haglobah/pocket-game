from dataclasses import dataclass


@dataclass(frozen=True)
class Cmd:
    pass


@dataclass(frozen=True)
class GenerateMap(Cmd):
    seed: int

# SOUNDS --------------------------------------------------------------------------

@dataclass(frozen=True)
class PlayStepSound(Cmd):
    pass


@dataclass(frozen=True)
class PlaySwimSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayThoughtSound(Cmd):
    pass

@dataclass(frozen=True)
class PlayEatingSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayMainThemeMusic(Cmd):
    pass

@dataclass(frozen=True)
class PlayBossThemeMusic(Cmd):
    pass

@dataclass(frozen=True)
class PlayTitleThemeMusic(Cmd):
    pass

@dataclass(frozen=True)
class PlayDeathScreenMusic(Cmd):
    pass


@dataclass(frozen=True)
class GenerateDarkWorld(Cmd):
    seed: int
    tilemap: tuple


@dataclass(frozen=True)
class PlayPunchSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayHitSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayBossFireSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayVictorySound(Cmd):
    pass
