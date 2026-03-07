from dataclasses import replace

from .constants import (
    MAP_W, MAP_H, Point,
    WATER, O2_MAX, O2_BREATHE_REFILL, O2_AUTO_REFILL_RATE,
    O2_LUNGS_UNDERWATER_CHUNK, LUNGS, GILLS, DOWN,
    MOVE_DELAY_LAND, MOVE_DELAY_WATER,
    DEATH_SCREEN_MIN_FRAMES, REWIND_DURATION,
    is_walkable, is_swimmable,
)
from .model import Model
from .messages import (
    Msg, Tick, MoveDir, StartGame, TypeChar, Backspace,
    MapGenerated, Breathe, ToggleBreathingMode, Die,
    DismissDeathScreen, RewindTick,
)
from .commands import Cmd, GenerateMap, PlayStepSound, PlaySwimSound


def init() -> tuple[Model, list[Cmd]]:
    model = Model(
        player_pos=Point(MAP_W // 2, MAP_H // 2),
        facing=DOWN,
        tilemap=(),
        seed=0,
        move_timer=0,
        state="title",
        seed_input="",
        frame=0,
        o2=O2_MAX,
        breathing_mode=GILLS,
        cycle=1,
        death_reason="",
        learned=(),
        death_timer=0,
        rewind_timer=0,
    )
    return model, []


def _add_learned(model: Model, skill: str) -> tuple[str, ...]:
    """Add a skill to learned if not already present."""
    if skill in model.learned:
        return model.learned
    return model.learned + (skill,)


def _wrap(p: Point) -> Point:
    return Point(p.x % MAP_W, p.y % MAP_H)


def _find_spawn(tilemap: tuple[tuple[int, ...], ...]) -> Point:
    """Find a walkable spawn near center."""
    cx, cy = MAP_W // 2, MAP_H // 2
    for r in range(max(MAP_W, MAP_H)):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                p = _wrap(Point(cx + dx, cy + dy))
                if is_swimmable(tilemap[p.y][p.x]):
                    return p
    return Point(cx, cy)


def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick():
            if model.state == "dead":
                return replace(model, death_timer=model.death_timer + 1, frame=model.frame + 1), []
            new_o2 = model.o2
            cmds: list[Cmd] = []
            if model.state == "play" and model.tilemap:
                underwater = model.tilemap[model.player_pos.y][model.player_pos.x] == WATER
                can_auto_breathe = (model.breathing_mode == LUNGS and not underwater)
                lungs_underwater = (model.breathing_mode == LUNGS and underwater)
                if can_auto_breathe:
                    new_o2 = min(O2_MAX, new_o2 + O2_AUTO_REFILL_RATE)
                elif lungs_underwater and model.frame % 60 == 0:
                    # Big painful gulps every second
                    new_o2 = max(0, new_o2 - O2_LUNGS_UNDERWATER_CHUNK)
                else:
                    new_o2 = max(0, new_o2 - 1)
                # Check for death
                if new_o2 <= 0:
                    if model.breathing_mode == LUNGS and underwater:
                        reason = "Drowned (lungs underwater)"
                    elif model.breathing_mode == GILLS:
                        reason = "Suffocated (gills ran dry)"
                    else:
                        reason = "Ran out of oxygen"
                    return replace(
                        model,
                        frame=model.frame + 1,
                        o2=0,
                        state="dead",
                        death_reason=reason,
                        death_timer=0,
                    ), []
            return replace(
                model,
                move_timer=max(0, model.move_timer - 1),
                frame=model.frame + 1,
                o2=new_o2,
            ), cmds

        case MoveDir(direction=d):
            if model.state != "play":
                return model, []
            if model.move_timer > 0:
                # Still in cooldown, just update facing
                return replace(model, facing=d), []
            new_pos = _wrap(Point(model.player_pos.x + d.x, model.player_pos.y + d.y))
            if is_walkable(model.tilemap[new_pos.y][new_pos.x]):
                return replace(
                    model, player_pos=new_pos, facing=d, move_timer=MOVE_DELAY_LAND,
                    learned=_add_learned(model, "walking on land"),
                ), [PlayStepSound()]
            if is_swimmable(model.tilemap[new_pos.y][new_pos.x]):
                return replace(
                    model, player_pos=new_pos, facing=d, move_timer=MOVE_DELAY_WATER,
                    learned=_add_learned(model, "swimming"),
                ), [PlaySwimSound()]
            return replace(model, facing=d, move_timer=0), []

        case StartGame(seed=s):
            return model, [GenerateMap(seed=s)]

        case MapGenerated(tilemap=tm, seed=s):
            spawn = _find_spawn(tm)
            return replace(
                model,
                player_pos=spawn,
                facing=DOWN,
                tilemap=tm,
                seed=s,
                move_timer=0,
                state="play",
                o2=O2_MAX,
                breathing_mode=GILLS,
                learned=(),
                death_reason="",
                death_timer=0,
                rewind_timer=0,
            ), []

        case TypeChar(char=c):
            if model.state == "title" and len(model.seed_input) < 16:
                return replace(model, seed_input=model.seed_input + c), []
            return model, []

        case Backspace():
            if model.state == "title" and model.seed_input:
                return replace(model, seed_input=model.seed_input[:-1]), []
            return model, []

        case Breathe():
            if model.state != "play" or not model.tilemap:
                return model, []
            underwater = model.tilemap[model.player_pos.y][model.player_pos.x] == WATER
            if model.breathing_mode == GILLS and underwater:
                new_o2 = min(O2_MAX, model.o2 + O2_BREATHE_REFILL)
                return replace(
                    model, o2=new_o2,
                    learned=_add_learned(model, "breathing underwater"),
                ), []
            return model, []

        case ToggleBreathingMode():
            new_mode = GILLS if model.breathing_mode == LUNGS else LUNGS
            skill = "switching to lungs" if new_mode == LUNGS else "switching to gills"
            return replace(
                model, breathing_mode=new_mode,
                learned=_add_learned(model, skill),
            ), []

        case Die(reason=r):
            return replace(
                model, state="dead", death_reason=r, death_timer=0,
            ), []

        case DismissDeathScreen():
            if model.state == "dead" and model.death_timer >= DEATH_SCREEN_MIN_FRAMES:
                return replace(
                    model, state="rewind", rewind_timer=REWIND_DURATION,
                ), []
            return model, []

        case RewindTick():
            if model.state == "rewind":
                new_timer = model.rewind_timer - 1
                if new_timer <= 0:
                    # Respawn with same seed, next cycle
                    return replace(
                        model, state="play",
                        cycle=model.cycle + 1,
                        rewind_timer=0,
                    ), [GenerateMap(seed=model.seed)]
                return replace(model, rewind_timer=new_timer, frame=model.frame + 1), []
            return model, []

    return model, []
