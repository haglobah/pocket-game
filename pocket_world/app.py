import hashlib
import tempfile
from pathlib import Path

import pyxel
from PIL import Image as PILImage

from .constants import SCREEN_W, SCREEN_H, Point, DARK_SPRITE_MAP
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
    Punch,
    DarkWorldGenerated,
    DismissCredits,
    ChooseWizardOption,
)
from .commands import Cmd, GenerateMap, PlayStepSound, PlaySwimSound, PlayThoughtSound, PlayEatingSound
from .commands import (
    GenerateDarkWorld,
    PlayBossFireSound,
    PlayBossThemeMusic,
    PlayDeathScreenMusic,
    PlayHitSound,
    PlayMainThemeMusic,
    PlayPunchSound,
    PlayTitleThemeMusic,
    PlayVictorySound,
)
from .mapgen import generate_map, generate_dark_world
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
            tm, objects, poison_water = generate_map(s)
            return [MapGenerated(tilemap=tm, seed=s, objects=objects, poison_water=poison_water)]
        case GenerateDarkWorld(seed=s, tilemap=tm):
            boss_parts, minions = generate_dark_world(s, tm)
            return [DarkWorldGenerated(boss_parts=boss_parts, minions=minions)]
        case PlayMainThemeMusic():
            pyxel.play(0, 0, loop=True)
        case PlayBossThemeMusic():
            pyxel.play(0, 1, loop=True)
        case PlayTitleThemeMusic():
            pyxel.play(0, 2, loop=True)
        case PlayDeathScreenMusic():
            pyxel.play(0, 3, loop=True)
        case PlayStepSound():
            pyxel.play(1, 16)
        case PlaySwimSound():
            pyxel.play(1, 17)
        case PlayThoughtSound():
            pyxel.play(2, 47)
        case PlayEatingSound():
            pyxel.play(1, 31)
        case PlayPunchSound():
            pyxel.play(1, 41)
        case PlayHitSound():
            pyxel.play(1, 42)
        case PlayBossFireSound():
            pyxel.play(2, 43)
        case PlayVictorySound():
            pyxel.play(0, 44)
    return []


def define_sounds():
    # Main theme music
    pyxel.sounds[0].pcm(str(_PROJECT_ROOT / "assets/audio/00_soundtrack_main.wav"))
    # Boss theme music
    pyxel.sounds[1].pcm(str(_PROJECT_ROOT / "assets/audio/01_soundtrack_boss_fight.wav"))
    # Title screen music
    pyxel.sounds[2].pcm(str(_PROJECT_ROOT / "assets/audio/02_titlescreen_loud.wav"))
    # Death screen music
    pyxel.sounds[3].pcm(str(_PROJECT_ROOT / "assets/audio/03_death_screen_track.wav"))
    # Soft footstep sound
    pyxel.sounds[16].pcm(str(_PROJECT_ROOT / "assets/audio/16_steps.ogg"))
    # Thought bubble chime — gentle ascending two-note
    pyxel.sounds[17].pcm(str(_PROJECT_ROOT / "assets/audio/17_water_bubble.ogg"))
    # Eating sound
    pyxel.sounds[31].pcm(str(_PROJECT_ROOT / "assets/audio/31_bite.ogg"))
    # Thought bubble sound
    pyxel.sounds[47].pcm(str(_PROJECT_ROOT / "assets/audio/47_thought_bubble.ogg"))
    # Punch — short percussive hit
    pyxel.sounds[41].set("c3c2", "pp", "76", "f", 6)
    # Player hit — descending buzz
    pyxel.sounds[42].set("f2c2", "nn", "54", "f", 8)
    # Boss fire — whoosh
    pyxel.sounds[43].set("g3e3c3", "sss", "543", "f", 6)
    # Victory fanfare
    pyxel.sounds[44].set("c3e3g3c4", "pppp", "7777", "nnnn", 15)


_DARK_ASSETS = _PROJECT_ROOT / "assets" / "dark_pocket_world"


def _scale_and_save(src_path: str, w: int, h: int) -> str:
    """Scale a PNG to (w, h) using PIL, save to temp file, return path."""
    img = PILImage.open(src_path).convert("RGBA")
    img = img.resize((w, h), PILImage.LANCZOS)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    return tmp.name


def _load_dark_sprites():
    """Load dark world sprites into image banks."""
    dark_env = str(_DARK_ASSETS / "dark_environment_sprites.png")
    pyxel.images[2].load(0, 0, dark_env)

    _all_sprites = [
        ("squid", "minions/squid_left.png"),
        ("squid_small", "minions/squid_small_left.png"),
        ("scorpion", "minions/scorpion_left.png"),
        ("golem", "minions/golem_left.png"),
        ("head", "boss/head.png"),
        ("wings", "boss/wings.png"),
        ("arms", "boss/arms.png"),
        ("projectile_1", "boss/projectile_1.png"),
        ("projectile_2", "boss/projectile_2.png"),
    ]
    for name, relpath in _all_sprites:
        bank, x, y, w, h = DARK_SPRITE_MAP[name]
        tmp = _scale_and_save(str(_DARK_ASSETS / relpath), w, h)
        pyxel.images[bank].load(x, y, tmp)


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
        pyxel.images[1].load(0, 0, str(_PROJECT_ROOT / "assets" / "sprites" / "also_without_berries.png"))
        # Keep wise-man sprites in bank 1 to avoid overlap with dark-world sprites in bank 2.
        pyxel.images[1].load(0, 128, str(_PROJECT_ROOT / "assets" / "sprites" / "wise-man-front.png"))
        pyxel.images[1].load(16, 128, str(_PROJECT_ROOT / "assets" / "sprites" / "wise-man-left.png"))
        pyxel.images[1].load(32, 128, str(_PROJECT_ROOT / "assets" / "sprites" / "wise-man-right.png"))
        # Preload dark sprites used by dark pocket world encounters.
        _load_dark_sprites()
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
            if pyxel.btnp(pyxel.KEY_1):
                msgs.append(ChooseWizardOption(option=1))
            if pyxel.btnp(pyxel.KEY_2):
                msgs.append(ChooseWizardOption(option=2))
            msgs.append(SetSprinting(active=pyxel.btn(pyxel.KEY_C)))

        elif self.model.game.state == "dark_play":
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
            if pyxel.btnp(pyxel.KEY_F):
                msgs.append(Punch())

        elif self.model.game.state == "dead":
            if pyxel.btnp(pyxel.KEY_RETURN):
                msgs.append(DismissDeathScreen())

        elif self.model.game.state == "rewind":
            msgs.append(RewindTick())

        elif self.model.game.state == "ending_b":
            if pyxel.btnp(pyxel.KEY_RETURN):
                msgs.append(DismissCredits())

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
