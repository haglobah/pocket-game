from dataclasses import dataclass


@dataclass(frozen=True)
class Cmd:
    pass


@dataclass(frozen=True)
class GenerateMap(Cmd):
    seed: int
    
@dataclass(frozen=True)
class GenerateDarkWorld(Cmd):
    seed: int
    tilemap: tuple

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

@dataclass(frozen=True)
class PlayDrowningSound(Cmd):
    pass

@dataclass(frozen=True)
class PlaySuffocatingSound(Cmd):
    pass

@dataclass(frozen=True)
class PlayDehydrationSound(Cmd):
    pass

@dataclass(frozen=True)
class PlayStarvationSound(Cmd):
    pass

@dataclass(frozen=True)
class PlayKilledByEnemySound(Cmd):
    pass
