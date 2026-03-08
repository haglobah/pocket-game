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
    HYDRATION_START,
    HUNGER_START,
    HUNGER_MAX,
    HUNGER_REFILL,
    HUNGER_DEPLETION,
    DRINK_TILES,
    POISON_DURATION,
    POISON_O2_DRAIN,
    is_walkable,
    is_swimmable,
)
from .model import Model, Map, PlantObject, ThoughtBubble
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
from .commands import *
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


def _is_poison_water(pos: Point, map_: Map) -> bool:
    """Check if the player is standing on or adjacent to poisonous water."""
    positions = (
        pos,
        Point(pos.x, pos.y - 1),
        Point(pos.x, pos.y + 1),
        Point(pos.x - 1, pos.y),
        Point(pos.x + 1, pos.y),
    )
    for p in positions:
        if 0 <= p.x < MAP_W and 0 <= p.y < MAP_H:
            if map_.tilemap[p.y][p.x] in DRINK_TILES and p in map_.poison_water:
                return True
    return False


def _find_nearby_food(objects: tuple[PlantObject, ...], pos: Point) -> int | None:
    """Return index of an adjacent or standing PlantObject with has_fruit=True, or None."""
    positions = frozenset((
        pos,
        Point(pos.x, pos.y - 1),
        Point(pos.x, pos.y + 1),
        Point(pos.x - 1, pos.y),
        Point(pos.x + 1, pos.y),
    ))
    for i, obj in enumerate(objects):
        if obj.has_fruit and obj.anchor in positions:
            return i
    return None


def _find_spawn(tilemap: tuple[tuple[int, ...], ...], objects: tuple[PlantObject, ...] = ()) -> Point:
    """Find a walkable spawn near center."""
    anchor_set = frozenset(obj.anchor for obj in objects) if objects else frozenset()
    cx, cy = MAP_W // 2, MAP_H // 2
    for r in range(max(MAP_W, MAP_H)):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                    p = Point(nx, ny)
                    if is_walkable(tilemap[ny][nx]) and p not in anchor_set:
                        return p
    return Point(cx, cy)

def transition_to_death(model: Model, reason: str) -> tuple[Model, list[Cmd]]:
    cycle = model.cycle
    game = model.game
    return replace(model,
        player=replace(model.player, o2=O2_MAX, poison_timer=0),
        cycle=replace(cycle, death_reason=reason, death_timer=0),
        game=replace(game, frame=game.frame + 1, state="dead"),
    ), [PlayDeathScreenMusic()]

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
            new_poison = player.poison_timer
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
                # Poison drain: suffocate over 10 seconds
                new_poison = max(0, player.poison_timer - 1) if player.poison_timer > 0 else 0
                if new_poison > 0:
                    new_o2 = max(0, new_o2 - POISON_O2_DRAIN)
                # Check for O2 death
                if new_o2 <= 0:
                    if new_poison > 0 or (player.poison_timer > 0 and new_poison == 0):
                        reason = "Suffocated from poisoned water"
                    elif player.breathing_mode == LUNGS and underwater:
                        reason = "Drowned (lungs underwater)"
                    elif player.breathing_mode == GILLS:
                        reason = "Suffocated (gills ran dry)"
                    else:
                        reason = "Ran out of oxygen"
                    return transition_to_death(model, reason)
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
                    return transition_to_death(model, "Died of dehydration")
                if new_hunger <= 0:
                    return transition_to_death(model, "Died of starvation")
            return replace(model,
                player=replace(player,
                    move_timer=max(0, player.move_timer - 1),
                    o2=new_o2,
                    hydration=new_hydration,
                    hunger=new_hunger,
                    poison_timer=new_poison,
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
            # Block movement if an object anchor is at the target
            if map_.has_object_at(new_pos):
                return replace(model, player=replace(player, facing=d, move_timer=0)), []
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

        case MapGenerated(tilemap=tm, seed=s, objects=objs, poison_water=pw):
            spawn = _find_spawn(tm, objs)
            return replace(model,
                player=replace(player, pos=spawn, hydration=HYDRATION_START, hunger=HUNGER_START, poison_timer=0),
                map=Map(tilemap=tm, seed=s, objects=objs, poison_water=pw),
                cycle=replace(cycle, death_reason="", death_timer=0, rewind_timer=0, learned=()),
                game=replace(game,
                    state="play",
                    thought=None,
                    thought_cooldown=THOUGHT_INITIAL_DELAY,
                ),
            ), [PlayMainThemeMusic()]

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
                # Check if drinking from poisonous water
                is_poison = _is_poison_water(player.pos, map_)
                new_hydration = min(HYDRATION_MAX, player.hydration + HYDRATION_REFILL)
                new_poison_timer = POISON_DURATION if is_poison else player.poison_timer
                return replace(model,
                    player=replace(player, hydration=new_hydration, poison_timer=new_poison_timer),
                    cycle=replace(cycle, learned=_add_learned(cycle, "drinking water")),
                ), []
            return model, []

        case Eat():
            if game.state != "play" or not map_.tilemap:
                return model, []
            food_idx = _find_nearby_food(map_.objects, player.pos)
            if food_idx is not None:
                new_hunger = min(HUNGER_MAX, player.hunger + HUNGER_REFILL)
                # Mark the plant as eaten
                eaten_obj = replace(map_.objects[food_idx], has_fruit=False)
                new_objects = map_.objects[:food_idx] + (eaten_obj,) + map_.objects[food_idx + 1:]
                return replace(model,
                    player=replace(player, hunger=new_hunger),
                    map=replace(map_, objects=new_objects),
                    cycle=replace(cycle, learned=_add_learned(cycle, "eating plants")),
                ), [PlayEatingSound()]
            return model, []

        case ToggleMinimap():
            if game.state == "play":
                return replace(model, game=replace(game, show_minimap=not game.show_minimap)), []
            return model, []

        case Die(reason=r):
            return replace(model,
                cycle=replace(cycle, death_reason=r, death_timer=0),
                game=replace(game, state="dead"),
            ), [PlayDeathScreenMusic()]

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
