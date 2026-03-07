from dataclasses import replace

from .constants import (
    MAP_W,
    MAP_H,
    Point,
    WATER,
    O2_MAX,
    O2_BREATHE_REFILL,
    O2_AUTO_REFILL_RATE,
    O2_LUNGS_UNDERWATER_CHUNK,
    LUNGS,
    GILLS,
    DOWN,
    MOVE_DELAY_LAND,
    MOVE_DELAY_WATER,
    DEATH_SCREEN_MIN_FRAMES,
    REWIND_DURATION,
    THOUGHT_CHAR_SPEED, THOUGHT_READ_FRAMES,
    THOUGHT_COOLDOWN_FRAMES, THOUGHT_INITIAL_DELAY,
    HYDRATION_MAX,
    HYDRATION_REFILL,
    HYDRATION_DEPLETION,
    HUNGER_MAX,
    HUNGER_REFILL,
    HUNGER_DEPLETION,
    FOOD_TILES,
    DRINK_TILES,
    is_walkable,
    is_swimmable,
)
from .model import Model, ThoughtBubble
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
    Die,
    DismissDeathScreen,
    RewindTick,
)
from .commands import Cmd, GenerateMap, PlayStepSound, PlaySwimSound, PlayThoughtSound
from .thoughts import check_triggers, get_memory

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
        thought=None,
        seen_memories=(),
        thought_cooldown=0,
    )
    return model, []


def _add_learned(model: Model, skill: str) -> tuple[str, ...]:
    """Add a skill to learned if not already present."""
    if skill in model.learned:
        return model.learned
    return model.learned + (skill,)


def _wrap(p: Point) -> Point:
    return Point(p.x % MAP_W, p.y % MAP_H)


def _clamp(p: Point) -> Point:
    """Clamp position to map bounds (no visual wrapping)."""
    return Point(max(0, min(MAP_W - 1, p.x)), max(0, min(MAP_H - 1, p.y)))


def _adjacent_tiles(pos: Point, tilemap: tuple[tuple[int, ...], ...]) -> list[int]:
    """Return tile types of the 4 cardinal neighbors (clamped to map bounds)."""
    tiles = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = pos.x + dx, pos.y + dy
        if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
            tiles.append(tilemap[ny][nx])
    return tiles


def _find_spawn(tilemap: tuple[tuple[int, ...], ...]) -> Point:
    """Find a walkable spawn near center."""
    cx, cy = MAP_W // 2, MAP_H // 2
    for r in range(max(MAP_W, MAP_H)):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                    if is_walkable(tilemap[ny][nx]):
                        return Point(nx, ny)
    return Point(cx, cy)


def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick():
            if model.state == "dead":
                return replace(
                    model, death_timer=model.death_timer + 1, frame=model.frame + 1
                ), []
            new_o2 = model.o2
            new_thought = model.thought
            new_seen = model.seen_memories
            new_cooldown = model.thought_cooldown
            cmds: list[Cmd] = []
            if model.state == "play" and model.tilemap:
                underwater = (
                    model.tilemap[model.player_pos.y][model.player_pos.x] == WATER
                )
                can_auto_breathe = model.breathing_mode == LUNGS and not underwater
                lungs_underwater = model.breathing_mode == LUNGS and underwater
                if can_auto_breathe:
                    new_o2 = min(O2_MAX, new_o2 + O2_AUTO_REFILL_RATE)
                elif lungs_underwater and model.frame % 60 == 0:
                    new_o2 = max(0, new_o2 - O2_LUNGS_UNDERWATER_CHUNK)
                else:
                    new_o2 = max(0, new_o2 - 1)
                # Check for O2 death
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
                # Thought bubble management
                new_cooldown = max(0, new_cooldown - 1)
                if new_thought is not None:
                    new_timer = new_thought.timer + 1
                    if new_timer >= new_thought.duration:
                        if new_thought.memory_id not in new_seen:
                            new_seen = new_seen + (new_thought.memory_id,)
                        new_thought = None
                        new_cooldown = THOUGHT_COOLDOWN_FRAMES
                    else:
                        new_thought = replace(new_thought, timer=new_timer)
                elif new_cooldown == 0:
                    triggered = check_triggers(model.cycle, model.learned, new_seen)
                    if triggered is not None:
                        mem = get_memory(triggered)
                        duration = len(mem.text) * THOUGHT_CHAR_SPEED + THOUGHT_READ_FRAMES
                        new_thought = ThoughtBubble(
                            memory_id=mem.id,
                            text=mem.text,
                            timer=0,
                            duration=duration,
                        )
                        cmds.append(PlayThoughtSound())

            # Deplete hydration and hunger
            new_hydration = max(0, model.hydration - HYDRATION_DEPLETION)
            new_hunger = max(0, model.hunger - HUNGER_DEPLETION)
            if model.state == "play":
                if new_hydration <= 0:
                    return replace(
                        model,
                        frame=model.frame + 1,
                        hydration=0,
                        hunger=new_hunger,
                        o2=new_o2,
                        state="dead",
                        death_reason="Died of dehydration",
                        death_timer=0,
                    ), []
                if new_hunger <= 0:
                    return replace(
                        model,
                        frame=model.frame + 1,
                        hunger=0,
                        hydration=new_hydration,
                        o2=new_o2,
                        state="dead",
                        death_reason="Died of starvation",
                        death_timer=0,
                    ), []
            return replace(
                model,
                move_timer=max(0, model.move_timer - 1),
                frame=model.frame + 1,
                o2=new_o2,
                thought=new_thought,
                seen_memories=new_seen,
                thought_cooldown=new_cooldown,
                hydration=new_hydration,
                hunger=new_hunger,
            ), cmds

        case MoveDir(direction=d):
            if model.state != "play":
                return model, []
            if model.move_timer > 0:
                # Still in cooldown, just update facing
                return replace(model, facing=d), []
            raw = Point(model.player_pos.x + d.x, model.player_pos.y + d.y)
            new_pos = Point(raw.x % MAP_W, raw.y % MAP_H)
            if is_walkable(model.tilemap[new_pos.y][new_pos.x]):
                return replace(
                    model,
                    player_pos=new_pos,
                    facing=d,
                    move_timer=MOVE_DELAY_LAND,
                    learned=_add_learned(model, "walking on land"),
                ), [PlayStepSound()]
            if is_swimmable(model.tilemap[new_pos.y][new_pos.x]):
                return replace(
                    model,
                    player_pos=new_pos,
                    facing=d,
                    move_timer=MOVE_DELAY_WATER,
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
                tilemap=tm,
                seed=s,
                state="play",
                o2=O2_MAX,
                hydration=HYDRATION_MAX,
                hunger=HUNGER_MAX,
                learned=(),
                death_reason="",
                death_timer=0,
                rewind_timer=0,
                thought=None,
                thought_cooldown=THOUGHT_INITIAL_DELAY,
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
                    model,
                    o2=new_o2,
                    learned=_add_learned(model, "breathing underwater"),
                ), []
            return model, []

        case ToggleBreathingMode():
            new_mode = GILLS if model.breathing_mode == LUNGS else LUNGS
            skill = "switching to lungs" if new_mode == LUNGS else "switching to gills"
            return replace(
                model,
                breathing_mode=new_mode,
                learned=_add_learned(model, skill),
            ), []

        case Drink():
            if model.state != "play" or not model.tilemap:
                return model, []
            nearby = _adjacent_tiles(model.player_pos, model.tilemap)
            standing = model.tilemap[model.player_pos.y][model.player_pos.x]
            if standing in DRINK_TILES or any(t in DRINK_TILES for t in nearby):
                new_hydration = min(HYDRATION_MAX, model.hydration + HYDRATION_REFILL)
                return replace(
                    model,
                    hydration=new_hydration,
                    learned=_add_learned(model, "drinking water"),
                ), []
            return model, []

        case Eat():
            if model.state != "play" or not model.tilemap:
                return model, []
            nearby = _adjacent_tiles(model.player_pos, model.tilemap)
            standing = model.tilemap[model.player_pos.y][model.player_pos.x]
            if standing in FOOD_TILES or any(t in FOOD_TILES for t in nearby):
                new_hunger = min(HUNGER_MAX, model.hunger + HUNGER_REFILL)
                return replace(
                    model,
                    hunger=new_hunger,
                    learned=_add_learned(model, "eating plants"),
                ), []
            return model, []

        case Die(reason=r):
            return replace(
                model,
                state="dead",
                death_reason=r,
                death_timer=0,
            ), []

        case DismissDeathScreen():
            if model.state == "dead" and model.death_timer >= DEATH_SCREEN_MIN_FRAMES:
                return replace(
                    model,
                    state="rewind",
                    rewind_timer=REWIND_DURATION,
                ), []
            return model, []

        case RewindTick():
            if model.state == "rewind":
                new_timer = model.rewind_timer - 1
                if new_timer <= 0:
                    # Respawn with same seed, next cycle
                    return replace(
                        model,
                        state="play",
                        cycle=model.cycle + 1,
                        rewind_timer=0,
                    ), [GenerateMap(seed=model.seed)]
                return replace(model, rewind_timer=new_timer, frame=model.frame + 1), []
            return model, []

    return model, []
