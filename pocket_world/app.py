import hashlib
from pathlib import Path

import pyxel

from .constants import SCREEN_W, SCREEN_H, Point
from .messages import (
    Msg,
    Tick,
    MoveDir,
    StartGame,
    TypeChar,
    Backspace,
    MapGenerated,
    Breathe,
    ToggleBreathingMode,
    Drink,
    Eat,
    DismissDeathScreen,
    RewindTick,
)
from .commands import Cmd, GenerateMap, PlayStepSound, PlaySwimSound, PlayThoughtSound
from .mapgen import generate_map
from .update import update
from .view import view
from .model import init

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Characters that can be typed for seed input
TYPEABLE = "0123456789abcdefghijklmnopqrstuvwxyz"
PYXEL_KEYS = {c: getattr(pyxel, f"KEY_{c.upper()}") for c in TYPEABLE}


def interpret_cmd(cmd: Cmd) -> list[Msg]:
    match cmd:
        case GenerateMap(seed=s):
            tm = generate_map(s)
            return [MapGenerated(tilemap=tm, seed=s)]
        case PlayStepSound():
            pyxel.play(3, 0)
        case PlaySwimSound():
            pyxel.play(3, 0)
        case PlayThoughtSound():
            pyxel.play(2, 1)
    return []


def define_sounds():
    # Soft footstep sound
    pyxel.sounds[0].set(
        notes="c2",
        tones="n",
        volumes="2",
        effects="f",
        speed=5,
    )
    # Thought bubble chime — gentle ascending two-note
    pyxel.sounds[1].set(
        notes="e3g3",
        tones="s",
        volumes="32",
        effects="f",
        speed=10,
    )


class App:
    def __init__(self):
        pyxel.init(
            SCREEN_W,
            SCREEN_H,
            title="Pocket World",
            fps=60,
            display_scale=1,
        )
        pyxel.load(
            str(_PROJECT_ROOT / "pocket_world.pyxres"),
            exclude_sounds=True,
            exclude_musics=True,
            exclude_tilemaps=True,
        )
        define_sounds()
        self.model, cmds = init()
        self._process_cmds(cmds)
        pyxel.run(self._update, self._draw)

    def _collect_input(self) -> list[Msg]:
        msgs: list[Msg] = []

        if self.model.state == "title":
            # Text input for seed
            for char, key in PYXEL_KEYS.items():
                if pyxel.btnp(key, hold=15, repeat=3):
                    msgs.append(TypeChar(char=char))
            if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=15, repeat=3):
                msgs.append(Backspace())
            if pyxel.btnp(pyxel.KEY_RETURN):
                seed_text = self.model.seed_input.strip()
                if seed_text:
                    seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (
                        2**31
                    )
                else:
                    seed = pyxel.rndi(0, 2**31 - 1)
                msgs.append(StartGame(seed=seed))

        elif self.model.state == "play":
            dx = 0
            dy = 0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                dx -= 1
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                dx += 1
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                dy -= 1
            if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                dy += 1
            if dx != 0 or dy != 0:
                msgs.append(MoveDir(direction=Point(dx, dy)))
            if pyxel.btnp(pyxel.KEY_SPACE):
                msgs.append(Breathe())
            if pyxel.btnp(pyxel.KEY_B):
                msgs.append(ToggleBreathingMode())
            if pyxel.btnp(pyxel.KEY_Q):
                msgs.append(Drink())
            if pyxel.btnp(pyxel.KEY_E):
                msgs.append(Eat())

        elif self.model.state == "dead":
            if pyxel.btnp(pyxel.KEY_RETURN):
                msgs.append(DismissDeathScreen())

        elif self.model.state == "rewind":
            msgs.append(RewindTick())

        msgs.append(Tick())
        return msgs

    def _update(self):
        for msg in self._collect_input():
            self.model, cmds = update(self.model, msg)
            self._process_cmds(cmds)

    def _process_cmds(self, cmds: list[Cmd]):
        for cmd in cmds:
            new_msgs = interpret_cmd(cmd)
            for msg in new_msgs:
                self.model, new_cmds = update(self.model, msg)
                self._process_cmds(new_cmds)

    def _draw(self):
        view(self.model)
