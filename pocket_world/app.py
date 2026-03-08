import hashlib
import random
from pathlib import Path

import arcade

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
    Punch,
    DarkWorldGenerated,
    DismissCredits,
)
from .commands import (
    Cmd, GenerateMap, PlayStepSound, PlaySwimSound, PlayThoughtSound, PlayEatingSound,
    GenerateDarkWorld, PlayPunchSound, PlayHitSound, PlayBossFireSound, PlayVictorySound,
    PlayMainThemeMusic, PlayBossThemeMusic, PlayTitleThemeMusic, PlayDeathScreenMusic,
)
from .mapgen import generate_map, generate_dark_world
from .update import update
from .view import view
from .model import init

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Characters that can be typed for seed input
TYPEABLE = "0123456789abcdefghijklmnopqrstuvwxyz"


# --- Sound system ---
_sounds: dict[str, arcade.Sound] = {}
_current_music: arcade.Sound | None = None
_current_music_player = None


def _load_sound(key: str, path: str):
    """Load a sound file and store it by key."""
    try:
        _sounds[key] = arcade.Sound(path)
    except Exception:
        pass


def _play_sound(key: str, loop: bool = False):
    """Play a loaded sound by key."""
    global _current_music, _current_music_player
    snd = _sounds.get(key)
    if snd is None:
        return
    if loop:
        # Stop previous music before starting new
        if _current_music_player is not None:
            try:
                _current_music_player.pause()
            except Exception:
                pass
        _current_music = snd
        _current_music_player = snd.play(loop=True)
    else:
        snd.play()


def define_sounds():
    """Load all game sounds from asset files."""
    audio = _PROJECT_ROOT / "assets" / "audio"
    _load_sound("main_theme", str(audio / "00_soundtrack_main.wav"))
    _load_sound("boss_theme", str(audio / "01_soundtrack_boss_fight.wav"))
    _load_sound("title_theme", str(audio / "02_titlescreen_loud.wav"))
    _load_sound("death_theme", str(audio / "03_death_screen_track.wav"))
    _load_sound("step", str(audio / "16_steps.ogg"))
    _load_sound("swim", str(audio / "17_water_bubble.ogg"))
    _load_sound("bite", str(audio / "31_bite.ogg"))
    _load_sound("thought", str(audio / "47_thought_bubble.ogg"))
    # Synthesized sounds — use closest available or skip
    # punch, hit, boss_fire, victory were pyxel.sounds[n].set() — no wav file
    # We'll try to load from ogg files if they exist, otherwise skip
    _load_sound("punch", str(audio / "41_punch.ogg"))
    # hit, boss_fire, victory don't have asset files — they were synthesized in pyxel
    # We'll leave them as missing (silent) unless asset files are added


def interpret_cmd(cmd: Cmd) -> list[Msg]:
    """Execute side effects and return resulting messages."""
    match cmd:
        case GenerateMap(seed=s):
            tm, objects, poison_water = generate_map(s)
            return [MapGenerated(tilemap=tm, seed=s, objects=objects, poison_water=poison_water)]
        case GenerateDarkWorld(seed=s, tilemap=tm):
            boss_parts, minions = generate_dark_world(s, tm)
            return [DarkWorldGenerated(boss_parts=boss_parts, minions=minions)]
        case PlayMainThemeMusic():
            _play_sound("main_theme", loop=True)
        case PlayBossThemeMusic():
            _play_sound("boss_theme", loop=True)
        case PlayTitleThemeMusic():
            _play_sound("title_theme", loop=True)
        case PlayDeathScreenMusic():
            _play_sound("death_theme", loop=True)
        case PlayStepSound():
            _play_sound("step")
        case PlaySwimSound():
            _play_sound("swim")
        case PlayThoughtSound():
            _play_sound("thought")
        case PlayEatingSound():
            _play_sound("bite")
        case PlayPunchSound():
            _play_sound("punch")
        case PlayHitSound():
            _play_sound("hit")
        case PlayBossFireSound():
            _play_sound("boss_fire")
        case PlayVictorySound():
            _play_sound("victory")
    return []


# --- Arcade key mappings ---
def _build_key_map() -> dict[str, int]:
    km = {}
    for c in TYPEABLE:
        if c.isdigit():
            km[c] = getattr(arcade.key, f"KEY_{c}")
        else:
            km[c] = getattr(arcade.key, c.upper())
    return km

_KEY_MAP = _build_key_map()


class App(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, "Pocket World", update_rate=1 / 60)
        arcade.set_background_color(arcade.color.BLACK)
        define_sounds()
        self.model, cmds = init()
        self._keys_held: set[int] = set()
        self._keys_pressed: list[int] = []
        self._process_cmds(cmds)

    def on_key_press(self, key: int, modifiers: int):
        self._keys_held.add(key)
        self._keys_pressed.append(key)

    def on_key_release(self, key: int, modifiers: int):
        self._keys_held.discard(key)

    def _collect_input(self) -> list[Msg]:
        msgs: list[Msg] = []
        pressed = self._keys_pressed
        held = self._keys_held

        if self.model.game.state == "title":
            for char, key in _KEY_MAP.items():
                if key in pressed:
                    msgs.append(TypeChar(char=char))
            if arcade.key.BACKSPACE in pressed:
                msgs.append(Backspace())
            if arcade.key.RETURN in pressed or arcade.key.ENTER in pressed:
                seed_text = self.model.game.seed_input.strip()
                if seed_text:
                    seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (2**31)
                else:
                    seed = random.randint(0, 2**31 - 1)
                msgs.append(StartGame(seed=seed))

        elif self.model.game.state == "play":
            dx = 0
            dy = 0
            if arcade.key.LEFT in held or arcade.key.A in held:
                dx -= 1
            if arcade.key.RIGHT in held or arcade.key.D in held:
                dx += 1
            if arcade.key.UP in held or arcade.key.W in held:
                dy -= 1
            if arcade.key.DOWN in held or arcade.key.S in held:
                dy += 1
            if dx != 0 or dy != 0:
                msgs.append(MoveDir(direction=Point(dx, dy)))
            if arcade.key.SPACE in pressed:
                msgs.append(Breathe())
            if arcade.key.B in pressed:
                msgs.append(ToggleBreathingMode())
            if arcade.key.Q in pressed:
                msgs.append(Drink())
            if arcade.key.E in pressed:
                msgs.append(Eat())
            if arcade.key.M in pressed:
                msgs.append(ToggleMinimap())
            msgs.append(SetSprinting(active=arcade.key.C in held))

        elif self.model.game.state == "dark_play":
            dx = 0
            dy = 0
            if arcade.key.LEFT in held or arcade.key.A in held:
                dx -= 1
            if arcade.key.RIGHT in held or arcade.key.D in held:
                dx += 1
            if arcade.key.UP in held or arcade.key.W in held:
                dy -= 1
            if arcade.key.DOWN in held or arcade.key.S in held:
                dy += 1
            if dx != 0 or dy != 0:
                msgs.append(MoveDir(direction=Point(dx, dy)))
            if arcade.key.F in pressed:
                msgs.append(Punch())

        elif self.model.game.state == "dead":
            if arcade.key.RETURN in pressed or arcade.key.ENTER in pressed:
                msgs.append(DismissDeathScreen())

        elif self.model.game.state == "rewind":
            msgs.append(RewindTick())

        elif self.model.game.state == "ending_b":
            if arcade.key.RETURN in pressed or arcade.key.ENTER in pressed:
                msgs.append(DismissCredits())

        msgs.append(Tick())
        return msgs

    def on_update(self, delta_time: float):
        for msg in self._collect_input():
            self.model, cmds = update(self.model, msg)
            self._process_cmds(cmds)
        # Clear per-frame pressed keys
        self._keys_pressed.clear()

    def _process_cmds(self, cmds: list[Cmd]):
        for cmd in cmds:
            new_msgs = interpret_cmd(cmd)
            for msg in new_msgs:
                self.model, new_cmds = update(self.model, msg)
                self._process_cmds(new_cmds)

    def on_draw(self):
        self.clear()
        view(self.model)
