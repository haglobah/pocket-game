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
    ToggleMinimap,
    DismissDeathScreen,
    RewindTick,
    SetSprinting,
)
from .commands import *
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
            tm, objects = generate_map(s)
            return [MapGenerated(tilemap=tm, seed=s, objects=objects)]
        # sounds
        case PlayMainThemeMusic():
            pyxel.play(0, 0, loop=True)
        case PlayBossThemeMusic():
            pyxel.play(0, 1)
        case PlayStepSound():
            pyxel.play(1, 16)
        case PlaySwimSound():
            pyxel.play(1, 17)
        case PlayThoughtSound():
            pyxel.play(2  , 47)
        case PlayEatingSound():
            pyxel.play(1  ,31)
    return []


def define_sounds():
    # Main theme music
    pyxel.sounds[0].pcm(str(_PROJECT_ROOT / "assets/audio/00_soundtrack_main.wav"))
    # Boss theme music
    pyxel.sounds[1].pcm(str(_PROJECT_ROOT / "assets/audio/01_soundtrack_boss_fight.wav"))
    # Soft footstep sound
    pyxel.sounds[16].pcm(str(_PROJECT_ROOT / "assets/audio/16_steps.ogg"))
    # Thought bubble chime — gentle ascending two-note
    pyxel.sounds[17].pcm(str(_PROJECT_ROOT / "assets/audio/17_water_bubble.ogg"))
    # Eating sound
    pyxel.sounds[31].pcm(str(_PROJECT_ROOT / "assets/audio/31_bite.ogg"))
    # Thought bubble sound
    pyxel.sounds[47].pcm(str(_PROJECT_ROOT / "assets/audio/47_thought_bubble.ogg"))


class App:
    def __init__(self):
        pyxel.init(
            SCREEN_W,
            SCREEN_H,
            title="Pocket World",
            fps=60,
            display_scale=1,
        )
        pyxel.images[0].load(0, 0, str(_PROJECT_ROOT / "assets" / "sprites" / "karl_sprites.png"))
        # pyxel.images[1].load(0, 0, str(_PROJECT_ROOT / "assets" / "sprites" / "environment_sprites.png"))
        pyxel.images[1].load(0, 0, str(_PROJECT_ROOT / "assets" / "sprites" / "also_without_berries.png"))
        define_sounds()
        self.model, cmds = init()
        self._process_cmds(cmds)
        pyxel.run(self._update, self._draw)

    def _collect_input(self) -> list[Msg]:
        msgs: list[Msg] = []

        if self.model.game.state == "title":
            # Text input for seed
            for char, key in PYXEL_KEYS.items():
                if pyxel.btnp(key, hold=15, repeat=3):
                    msgs.append(TypeChar(char=char))
            if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=15, repeat=3):
                msgs.append(Backspace())
            if pyxel.btnp(pyxel.KEY_RETURN):
                seed_text = self.model.game.seed_input.strip()
                if seed_text:
                    seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (
                        2**31
                    )
                else:
                    seed = pyxel.rndi(0, 2**31 - 1)
                msgs.append(StartGame(seed=seed))

        elif self.model.game.state == "play":
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
            if pyxel.btnp(pyxel.KEY_M):
                msgs.append(ToggleMinimap())
            msgs.append(SetSprinting(active=pyxel.btn(pyxel.KEY_C)))

        elif self.model.game.state == "dead":
            if pyxel.btnp(pyxel.KEY_RETURN):
                msgs.append(DismissDeathScreen())

        elif self.model.game.state == "rewind":
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
