"""Chiptune sound effects and four music loops, all defined in code.

Music plays on channels 0-2; sound effects use channel 3.
"""

import pyxel

SFX_CHANNEL = 3

# Loudness relative to Pyxel's default channel gain (1.0 = default, 0 = mute)
MUSIC_VOLUME = 0.4
SFX_VOLUME = 0.6

# name: (notes, tones, volumes, effects, speed)
EFFECTS = {
    "step": ("c1", "n", "2", "f", 4),
    "swim": ("g2c3", "t", "32", "s", 5),
    "breathe": ("e3c3g2", "t", "543", "s", 6),
    "toggle": ("c3g3", "p", "3", "n", 4),
    "drink": ("c2e2g2", "t", "4", "s", 7),
    "bite": ("c2r c1", "n", "64", "f", 5),
    "thought": ("c3e3g3c4", "t", "3", "n", 6),
    "select": ("e3a3", "p", "3", "n", 5),
    "blip": ("c4", "p", "2", "f", 3),
    "bolt": ("c4g3c4g3e3", "s", "4", "v", 3),
    "hit": ("a2d2a1", "s", "6", "s", 5),
    "punch": ("c2a0", "n", "76", "f", 5),
    "tink": ("a3e4", "p", "4", "f", 4),
    "zap": ("g3c4e4", "s", "3", "f", 2),
    "boss_fire": ("c3g2c2", "p", "5", "s", 4),
    "boss_break": ("c3g2d#2c2g1c1", "n", "7", "f", 8),
    "killed_by_enemy": ("g2c2", "n", "6", "f", 6),
    "drowning": ("c3b2a2g2f2e2d2c2", "t", "5", "v", 12),
    "suffocating": ("e2d2c2b1a1g1", "p", "5", "f", 14),
    "dehydration": ("g2f2e2rd2c2", "t", "4", "f", 16),
    "starvation": ("c2rc2ra1rg1", "s", "4", "f", 14),
    "victory": ("c3e3g3c4rg3c4", "p", "5", "n", 10),
    "portal": ("c2d#2f#2a2c3d#3f#3a3", "t", "5", "v", 4),
    "rewind": ("c4a3f#3d#3c3a2f#2d#2", "t", "4", "v", 5),
    "tick": ("c3", "t", "3", "f", 4),
    "respawn": ("c2g2c3g3c4", "t", "4", "n", 5),
}

# track: (speed, [(notes, tones, volumes, effects), ...one per channel])
TRACKS = {
    "title": (
        28,
        [
            (
                "a2rc3e3 b2rrr g2rb2d3 a2rrr f2ra2c3 e3rd3c3 b2rg#2b2 e3rrr",
                "t",
                "5",
                "nnnf",
            ),
            (
                "a0ra0r a0ra0r g0rg0r g0rg0r f0rf0r f0rf0r e0re0r e0re0r",
                "t",
                "6",
                "f",
            ),
            (
                "e2rrr e2rrr d2rrr d2rrr c2rrr c2rrr b1rrr b1rrr",
                "s",
                "2",
                "v",
            ),
        ],
    ),
    "main": (
        20,
        [
            (
                "d3rf3g3 a3rg3f3 e3rc3d3 rrrr d3rf3g3 a3rc4a3 g3re3f3 d3rrr",
                "p",
                "3",
                "n",
            ),
            (
                "d1rd1a0 d1rd1a0 c1rc1g0 c1rc1g0 d1rd1a0 d1rd1a0 c1rc1g0 a0ra0r",
                "t",
                "5",
                "n",
            ),
            ("c1rc3r c1c1c3r " * 4, "n", "4020", "f"),
        ],
    ),
    "boss": (
        12,
        [
            (
                (
                    "e3e3g3e3 a3e3b3a3 g3g3f#3g3 e3rd3r "
                    "e3e3g3e3 a3e3b3c4 b3a3g3f#3 e3rrr"
                ),
                "s",
                "4",
                "n",
            ),
            ("e1e1e2e1 e1e1e2e1 c1c1c2c1 d1d1d2d1 " * 2, "t", "6", "n"),
            ("c1rc3r c1c1c3r " * 4, "n", "6", "f"),
        ],
    ),
    "death": (
        36,
        [
            ("e2rd2r c2rb1r a1rrr rrrr", "t", "4", "f"),
            ("a1rrr g1rrr f1rrr e1rrr", "t", "3", "n"),
        ],
    ),
}

SOUND_ID: dict[str, int] = {}
MUSIC_ID: dict[str, int] = {}


def define_sounds() -> None:
    for ch, channel in enumerate(pyxel.channels):
        volume = SFX_VOLUME if ch == SFX_CHANNEL else MUSIC_VOLUME
        channel.gain *= volume
    for i, (name, (notes, tones, volumes, effects, speed)) in enumerate(
        EFFECTS.items()
    ):
        pyxel.sounds[i].set(notes, tones, volumes, effects, speed)
        SOUND_ID[name] = i
    next_id = 32
    for m, (name, (speed, channels)) in enumerate(TRACKS.items()):
        ids = []
        for notes, tones, volumes, effects in channels:
            pyxel.sounds[next_id].set(notes, tones, volumes, effects, speed)
            ids.append([next_id])
            next_id += 1
        pyxel.musics[m].set(*ids)
        MUSIC_ID[name] = m


def play_sound(name: str) -> None:
    pyxel.play(SFX_CHANNEL, SOUND_ID[name])


def play_music(name: str) -> None:
    pyxel.playm(MUSIC_ID[name], loop=True)


def stop_music() -> None:
    for ch in range(SFX_CHANNEL):
        pyxel.stop(ch)
