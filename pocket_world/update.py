from dataclasses import replace

from .constants import (
    MAP_W,
    MAP_H,
    Point,
    WATER,
    WATER_DEEP,
    is_swimmable,
    O2_MAX,
    O2_BREATHE_REFILL,
    O2_AUTO_REFILL_RATE,
    O2_LUNGS_UNDERWATER_CHUNK,
    LUNGS,
    GILLS,
    DOWN,
    MOVE_DELAY_LAND,
    MOVE_DELAY_WATER,
    MOVE_DELAY_RUNNING,
    DEATH_SCREEN_MIN_FRAMES,
    REWIND_DURATION,
    THOUGHT_CHAR_SPEED,
    THOUGHT_READ_FRAMES,
    THOUGHT_COOLDOWN_FRAMES,
    THOUGHT_INITIAL_DELAY,
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
from .model import Model, Map, ThoughtBubble
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
    Die,
    DismissDeathScreen,
    RewindTick,
    SetSprinting,
)
from .commands import Cmd, GenerateMap, PlayStepSound, PlaySwimSound, PlayThoughtSound
from .thoughts import check_triggers, get_memory


def _add_learned(cycle, skill: str) -> tuple[str, ...]:
    """Add a skill to learned if not already present."""
    if skill in cycle.learned:
        return cycle.learned
    return cycle.learned + (skill,)


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
    player = model.player
    map_ = model.map
    cycle = model.cycle
    game = model.game

    match msg:
        case Tick():
            if game.state == "dead":
                return replace(model,
                    cycle=replace(cycle, death_timer=cycle.death_timer + 1),
                    game=replace(game, frame=game.frame + 1),
                ), []
            new_o2 = player.o2
            new_thought = game.thought
            new_seen = game.seen_memories
            new_cooldown = game.thought_cooldown
            cmds: list[Cmd] = []
            if game.state == "play" and map_.tilemap:
                underwater = is_swimmable(map_.tilemap[player.pos.y][player.pos.x])
                can_auto_breathe = player.breathing_mode == LUNGS and not underwater
                lungs_underwater = player.breathing_mode == LUNGS and underwater
                if can_auto_breathe:
                    new_o2 = min(O2_MAX, new_o2 + O2_AUTO_REFILL_RATE)
                elif lungs_underwater and game.frame % 60 == 0:
                    new_o2 = max(0, new_o2 - O2_LUNGS_UNDERWATER_CHUNK)
                else:
                    new_o2 = max(0, new_o2 - 1)
                # Check for O2 death
                if new_o2 <= 0:
                    if player.breathing_mode == LUNGS and underwater:
                        reason = "Drowned (lungs underwater)"
                    elif player.breathing_mode == GILLS:
                        reason = "Suffocated (gills ran dry)"
                    else:
                        reason = "Ran out of oxygen"
                    return replace(model,
                        player=replace(player, o2=0),
                        cycle=replace(cycle, death_reason=reason, death_timer=0),
                        game=replace(game, frame=game.frame + 1, state="dead"),
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
                    triggered = check_triggers(cycle.number, cycle.learned, new_seen)
                    if triggered is not None:
                        mem = get_memory(triggered)
                        duration = (
                            len(mem.text) * THOUGHT_CHAR_SPEED + THOUGHT_READ_FRAMES
                        )
                        new_thought = ThoughtBubble(
                            memory_id=mem.id,
                            text=mem.text,
                            timer=0,
                            duration=duration,
                        )
                        cmds.append(PlayThoughtSound())

            # Deplete hydration and hunger
            new_hydration = max(0, player.hydration - HYDRATION_DEPLETION)
            new_hunger = max(0, player.hunger - HUNGER_DEPLETION)
            if game.state == "play":
                if new_hydration <= 0:
                    return replace(model,
                        player=replace(player, o2=new_o2, hydration=0, hunger=new_hunger),
                        cycle=replace(cycle, death_reason="Died of dehydration", death_timer=0),
                        game=replace(game, frame=game.frame + 1, state="dead"),
                    ), []
                if new_hunger <= 0:
                    return replace(model,
                        player=replace(player, o2=new_o2, hydration=new_hydration, hunger=0),
                        cycle=replace(cycle, death_reason="Died of starvation", death_timer=0),
                        game=replace(game, frame=game.frame + 1, state="dead"),
                    ), []
            return replace(model,
                player=replace(player,
                    move_timer=max(0, player.move_timer - 1),
                    o2=new_o2,
                    hydration=new_hydration,
                    hunger=new_hunger,
                ),
                game=replace(game,
                    frame=game.frame + 1,
                    thought=new_thought,
                    seen_memories=new_seen,
                    thought_cooldown=new_cooldown,
                ),
            ), cmds

        case MoveDir(direction=d):
            if game.state != "play":
                return model, []
            if player.move_timer > 0:
                return replace(model, player=replace(player, facing=d)), []
            raw = Point(player.pos.x + d.x, player.pos.y + d.y)
            new_pos = Point(raw.x % MAP_W, raw.y % MAP_H)
            if is_walkable(map_.tilemap[new_pos.y][new_pos.x]):
                delay = MOVE_DELAY_RUNNING if player.sprinting else MOVE_DELAY_LAND
                skill = "sprinting" if player.sprinting else "walking on land"
                return replace(model,
                    player=replace(player, pos=new_pos, facing=d, move_timer=delay),
                    cycle=replace(cycle, learned=_add_learned(cycle, skill)),
                ), [PlayStepSound()]
            if is_swimmable(map_.tilemap[new_pos.y][new_pos.x]):
                return replace(model,
                    player=replace(player, pos=new_pos, facing=d, move_timer=MOVE_DELAY_WATER),
                    cycle=replace(cycle, learned=_add_learned(cycle, "swimming")),
                ), [PlaySwimSound()]
            return replace(model, player=replace(player, facing=d, move_timer=0)), []

        case StartGame(seed=s):
            return model, [GenerateMap(seed=s)]

        case MapGenerated(tilemap=tm, seed=s):
            spawn = _find_spawn(tm)
            return replace(model,
                player=replace(player, pos=spawn),
                map=Map(tilemap=tm, seed=s),
                cycle=replace(cycle, death_reason="", death_timer=0, rewind_timer=0, learned=()),
                game=replace(game,
                    state="play",
                    thought=None,
                    thought_cooldown=THOUGHT_INITIAL_DELAY,
                ),
            ), []

        case TypeChar(char=c):
            if game.state == "title" and len(game.seed_input) < 16:
                return replace(model, game=replace(game, seed_input=game.seed_input + c)), []
            return model, []

        case Backspace():
            if game.state == "title" and game.seed_input:
                return replace(model, game=replace(game, seed_input=game.seed_input[:-1])), []
            return model, []

        case Breathe():
            if game.state != "play" or not map_.tilemap:
                return model, []
            underwater = is_swimmable(map_.tilemap[player.pos.y][player.pos.x])
            if player.breathing_mode == GILLS and underwater:
                new_o2 = min(O2_MAX, player.o2 + O2_BREATHE_REFILL)
                return replace(model,
                    player=replace(player, o2=new_o2),
                    cycle=replace(cycle, learned=_add_learned(cycle, "breathing underwater")),
                ), []
            return model, []

        case ToggleBreathingMode():
            new_mode = GILLS if player.breathing_mode == LUNGS else LUNGS
            skill = "switching to lungs" if new_mode == LUNGS else "switching to gills"
            return replace(model,
                player=replace(player, breathing_mode=new_mode),
                cycle=replace(cycle, learned=_add_learned(cycle, skill)),
            ), []

        case Drink():
            if game.state != "play" or not map_.tilemap:
                return model, []
            nearby = _adjacent_tiles(player.pos, map_.tilemap)
            standing = map_.tilemap[player.pos.y][player.pos.x]
            if standing in DRINK_TILES or any(t in DRINK_TILES for t in nearby):
                new_hydration = min(HYDRATION_MAX, player.hydration + HYDRATION_REFILL)
                return replace(model,
                    player=replace(player, hydration=new_hydration),
                    cycle=replace(cycle, learned=_add_learned(cycle, "drinking water")),
                ), []
            return model, []

        case Eat():
            if game.state != "play" or not map_.tilemap:
                return model, []
            nearby = _adjacent_tiles(player.pos, map_.tilemap)
            standing = map_.tilemap[player.pos.y][player.pos.x]
            if standing in FOOD_TILES or any(t in FOOD_TILES for t in nearby):
                new_hunger = min(HUNGER_MAX, player.hunger + HUNGER_REFILL)
                return replace(model,
                    player=replace(player, hunger=new_hunger),
                    cycle=replace(cycle, learned=_add_learned(cycle, "eating plants")),
                ), []
            return model, []

        case ToggleMinimap():
            if game.state == "play":
                return replace(model, game=replace(game, show_minimap=not game.show_minimap)), []
            return model, []

        case Die(reason=r):
            return replace(model,
                cycle=replace(cycle, death_reason=r, death_timer=0),
                game=replace(game, state="dead"),
            ), []

        case DismissDeathScreen():
            if game.state == "dead" and cycle.death_timer >= DEATH_SCREEN_MIN_FRAMES:
                return replace(model,
                    cycle=replace(cycle, rewind_timer=REWIND_DURATION),
                    game=replace(game, state="rewind"),
                ), []
            return model, []

        case SetSprinting(active=a):
            return replace(model, player=replace(player, sprinting=a)), []

        case RewindTick():
            if game.state == "rewind":
                new_timer = cycle.rewind_timer - 1
                if new_timer <= 0:
                    return replace(model,
                        cycle=replace(cycle, number=cycle.number + 1, rewind_timer=0),
                        game=replace(game, state="play"),
                    ), [GenerateMap(seed=map_.seed)]
                return replace(model,
                    cycle=replace(cycle, rewind_timer=new_timer),
                    game=replace(game, frame=game.frame + 1),
                ), []
            return model, []

    return model, []
