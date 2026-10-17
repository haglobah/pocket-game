"""The impure shell: input, side effects and the Pyxel loop."""

import pyxel

from . import audio
from .commands import Cmd, PlayMusic, PlaySound, RandomSeedText, StopMusic
from .constants import FPS, HEIGHT, SEED_CHARS, WIDTH
from .font import build_font
from .messages import (
    Backspace,
    Breathe,
    Choose,
    Confirm,
    Drink,
    Eat,
    Msg,
    Punch,
    SeedChosen,
    Tick,
    ToggleBreath,
    ToggleMap,
    TypeChar,
)
from .sprites import load_sprites
from .update import init, update
from .view import view

SEED_KEYS = [(getattr(pyxel, f"KEY_{c.upper()}"), c) for c in SEED_CHARS]
PLAY_KEYS = [
    (pyxel.KEY_SPACE, Breathe()),
    (pyxel.KEY_B, ToggleBreath()),
    (pyxel.KEY_Q, Drink()),
    (pyxel.KEY_E, Eat()),
    (pyxel.KEY_M, ToggleMap()),
    (pyxel.KEY_1, Choose(1)),
    (pyxel.KEY_2, Choose(2)),
]


def interpret_cmd(cmd: Cmd) -> list[Msg]:
    match cmd:
        case PlaySound(sound=name):
            audio.play_sound(name)
        case PlayMusic(track=name):
            audio.play_music(name)
        case StopMusic():
            audio.stop_music()
        case RandomSeedText():
            text = "".join(
                SEED_CHARS[pyxel.rndi(0, len(SEED_CHARS) - 1)] for _ in range(8)
            )
            return [SeedChosen(text)]
    return []


def _held(*keys: int) -> bool:
    return any(pyxel.btn(k) for k in keys)


class App:
    def __init__(self):
        pyxel.init(WIDTH, HEIGHT, title="Pocket World", fps=FPS)
        audio.define_sounds()
        load_sprites()
        build_font()
        self.model, cmds = init()
        self._process_cmds(cmds)
        pyxel.run(self._update, self._draw)

    def _collect_input(self) -> list[Msg]:
        msgs: list[Msg] = []
        state = self.model.state
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_KP_ENTER):
            msgs.append(Confirm())
        if state == "title":
            msgs += [TypeChar(c) for key, c in SEED_KEYS if pyxel.btnp(key)]
            if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=18, repeat=3):
                msgs.append(Backspace())
        elif state == "play":
            msgs += [msg for key, msg in PLAY_KEYS if pyxel.btnp(key)]
        elif state == "dark_play" and pyxel.btnp(pyxel.KEY_F):
            msgs.append(Punch())
        dx = _held(pyxel.KEY_D, pyxel.KEY_RIGHT) - _held(pyxel.KEY_A, pyxel.KEY_LEFT)
        dy = _held(pyxel.KEY_S, pyxel.KEY_DOWN) - _held(pyxel.KEY_W, pyxel.KEY_UP)
        msgs.append(Tick(dx=dx, dy=dy, sprint=pyxel.btn(pyxel.KEY_C)))
        return msgs

    def _update(self):
        for msg in self._collect_input():
            self.model, cmds = update(self.model, msg)
            self._process_cmds(cmds)

    def _process_cmds(self, cmds: list[Cmd]):
        for cmd in cmds:
            for msg in interpret_cmd(cmd):
                self.model, new_cmds = update(self.model, msg)
                self._process_cmds(new_cmds)

    def _draw(self):
        view(self.model)
