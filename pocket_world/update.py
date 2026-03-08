from dataclasses import replace
from math import hypot

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
    WISE_DIALOG_CHAR_SPEED,
    WISE_DIALOG_READ_FRAMES,
    WISE_DIALOG_COOLDOWN_FRAMES,
    WISE_DIALOG_INITIAL_DELAY,
    WISE_IDLE_LINES,
    WISE_TALK_DISTANCE,
    WISE_SPAWN_MIN_DISTANCE,
    WISE_SPAWN_MAX_DISTANCE,
    WISE_FOLLOW_STEP_FRAMES,
    WISE_ATTACK_SHOT_SPEED,
    WISE_ATTACK_SHOT_TTL,
    WISE_ATTACK_COOLDOWN_FRAMES,
    WISE_ATTACK_O2_DAMAGE,
    HYDRATION_MAX,
    HYDRATION_REFILL,
    HYDRATION_DEPLETION,
    HYDRATION_START,
    HUNGER_START,
    HUNGER_MAX,
    HUNGER_REFILL,
    HUNGER_DEPLETION,
    FOOD_TILES,
    DRINK_TILES,
    is_walkable,
    is_swimmable,
)
from .model import Model, Map, ThoughtBubble, NpcDialogueBubble, WizardShot
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
    ChooseWizardOption,
)
from .commands import Cmd, GenerateMap, PlayStepSound, PlaySwimSound, PlayThoughtSound, PlayEatingSound
from .thoughts import check_triggers, get_memory


# node_id -> (wizard_text, option_1_text, option_2_text, next_on_1, next_on_2)
WIZARD_DIALOGUE_TREE: dict[str, tuple[str, str, str, str, str]] = {
    "opening": (
        "Traveler, the dunes remember your footsteps. Why do you return?",
        "I want to survive this loop.",
        "Your tricks are why I'm trapped.",
        "survive_1",
        "blame_1",
    ),
    "survive_1": (
        "Then choose: guidance with trust, or guidance with suspicion?",
        "I trust you. Teach me.",
        "Teach me, but I watch you.",
        "follow_end",
        "attack_end",
    ),
    "blame_1": (
        "Accusation sharpens magic. Do you seek peace, or challenge?",
        "Peace. Let's work together.",
        "Challenge. Show me your power.",
        "follow_end",
        "attack_end",
    ),
}


def _start_wizard_dialogue(game):
    text, option_1, option_2, _, _ = WIZARD_DIALOGUE_TREE["opening"]
    duration = len(text) * WISE_DIALOG_CHAR_SPEED + WISE_DIALOG_READ_FRAMES
    return replace(
        game,
        wise_dialogue_active=True,
        wise_dialogue_node="opening",
        wise_options=(option_1, option_2),
        wise_dialogue=NpcDialogueBubble(text=text, timer=0, duration=duration),
    )


def _wizard_distance_tiles(player_pos: Point, wise_pos: Point) -> int:
    return max(abs(player_pos.x - wise_pos.x), abs(player_pos.y - wise_pos.y))


def _pick_follower_tile(tilemap: tuple[tuple[int, ...], ...], wise_pos: Point, player_pos: Point) -> Point:
    """Step wise man one tile toward player if the destination is walkable."""
    dx = 0 if player_pos.x == wise_pos.x else (1 if player_pos.x > wise_pos.x else -1)
    dy = 0 if player_pos.y == wise_pos.y else (1 if player_pos.y > wise_pos.y else -1)
    for sx, sy in ((dx, dy), (dx, 0), (0, dy), (0, 0)):
        nx, ny = wise_pos.x + sx, wise_pos.y + sy
        if 0 <= nx < MAP_W and 0 <= ny < MAP_H and is_walkable(tilemap[ny][nx]):
            if nx == player_pos.x and ny == player_pos.y:
                continue
            return Point(nx, ny)
    return wise_pos


def _spawn_wizard_shot(wise_pos: Point, player_pos: Point) -> WizardShot:
    """Create one blue bolt from the wizard toward the player's current position."""
    start_x = wise_pos.x * 32 + 8
    start_y = wise_pos.y * 32 + 10
    target_x = player_pos.x * 32 + 16
    target_y = player_pos.y * 32 + 16
    dx = float(target_x - start_x)
    dy = float(target_y - start_y)
    dist = max(1.0, hypot(dx, dy))
    return WizardShot(
        x=start_x,
        y=start_y,
        vx=(dx / dist) * WISE_ATTACK_SHOT_SPEED,
        vy=(dy / dist) * WISE_ATTACK_SHOT_SPEED,
        ttl=WISE_ATTACK_SHOT_TTL,
    )


def _advance_wizard_shots(shots: tuple[WizardShot, ...], player_pos: Point) -> tuple[tuple[WizardShot, ...], int]:
    """Move wizard shots and return updated tuple + O2 damage dealt this tick."""
    hit_damage = 0
    updated: list[WizardShot] = []
    player_x = player_pos.x * 32 + 16
    player_y = player_pos.y * 32 + 16
    for shot in shots:
        nx = shot.x + shot.vx
        ny = shot.y + shot.vy
        ttl = shot.ttl - 1
        if ttl <= 0:
            continue
        if abs(nx - player_x) <= 10 and abs(ny - player_y) <= 14:
            hit_damage += WISE_ATTACK_O2_DAMAGE
            continue
        updated.append(replace(shot, x=nx, y=ny, ttl=ttl))
    return tuple(updated), hit_damage


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


def _find_wise_man_spot(tilemap: tuple[tuple[int, ...], ...], spawn: Point) -> Point:
    """Place the wise man on a walkable tile farther from spawn."""
    max_r = min(max(MAP_W, MAP_H), WISE_SPAWN_MAX_DISTANCE)
    min_r = max(1, WISE_SPAWN_MIN_DISTANCE)

    # Search outward in distance bands, checking edge tiles first.
    for r in range(min_r, max_r + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                nx, ny = spawn.x + dx, spawn.y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and is_walkable(tilemap[ny][nx]):
                    return Point(nx, ny)

    # Fallback: nearest walkable tile to spawn.
    for r in range(1, max(MAP_W, MAP_H)):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                nx, ny = spawn.x + dx, spawn.y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and is_walkable(tilemap[ny][nx]):
                    return Point(nx, ny)
    return spawn


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
            new_wise_dialogue = game.wise_dialogue
            new_wise_options = game.wise_options
            new_wise_dialogue_active = game.wise_dialogue_active
            new_wise_dialogue_node = game.wise_dialogue_node
            new_wise_outcome = game.wise_outcome
            new_seen = game.seen_memories
            new_cooldown = game.thought_cooldown
            new_wise_dialogue_cooldown = game.wise_dialogue_cooldown
            new_wise_dialogue_index = game.wise_dialogue_index
            new_wizard_shots = game.wizard_shots
            new_wizard_attack_cooldown = game.wizard_attack_cooldown
            new_map = map_
            cmds: list[Cmd] = []
            if game.state == "play" and map_.tilemap:
                # Trigger the branching wizard conversation the first time player comes close.
                if (
                    new_wise_outcome == "none"
                    and not new_wise_dialogue_active
                    and _wizard_distance_tiles(player.pos, map_.wise_man) <= WISE_TALK_DISTANCE
                ):
                    staged = _start_wizard_dialogue(game)
                    new_wise_dialogue_active = staged.wise_dialogue_active
                    new_wise_dialogue_node = staged.wise_dialogue_node
                    new_wise_options = staged.wise_options
                    new_wise_dialogue = staged.wise_dialogue

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

                # Wise-man dialogue: branch conversation while active, otherwise idle chatter.
                if new_wise_dialogue_active:
                    if new_wise_dialogue is not None:
                        new_wise_dialogue = replace(
                            new_wise_dialogue,
                            timer=min(new_wise_dialogue.duration, new_wise_dialogue.timer + 1),
                        )
                else:
                    new_wise_dialogue_cooldown = max(0, new_wise_dialogue_cooldown - 1)
                    if new_wise_dialogue is not None:
                        new_timer = new_wise_dialogue.timer + 1
                        if new_timer >= new_wise_dialogue.duration:
                            new_wise_dialogue = None
                            new_wise_dialogue_cooldown = WISE_DIALOG_COOLDOWN_FRAMES
                        else:
                            new_wise_dialogue = replace(new_wise_dialogue, timer=new_timer)
                    elif new_wise_dialogue_cooldown == 0 and WISE_IDLE_LINES and new_wise_outcome == "none":
                        text = WISE_IDLE_LINES[new_wise_dialogue_index % len(WISE_IDLE_LINES)]
                        duration = len(text) * WISE_DIALOG_CHAR_SPEED + WISE_DIALOG_READ_FRAMES
                        new_wise_dialogue = NpcDialogueBubble(text=text, timer=0, duration=duration)
                        new_wise_dialogue_index = (new_wise_dialogue_index + 1) % len(WISE_IDLE_LINES)
                        cmds.append(PlayThoughtSound())

                # End states: attack (blue bolts) or follow.
                if new_wise_outcome == "attack":
                    new_wizard_shots, shot_damage = _advance_wizard_shots(new_wizard_shots, player.pos)
                    new_o2 = max(0, new_o2 - shot_damage)
                    if new_wizard_attack_cooldown <= 0:
                        new_wizard_shots = new_wizard_shots + (_spawn_wizard_shot(map_.wise_man, player.pos),)
                        new_wizard_attack_cooldown = WISE_ATTACK_COOLDOWN_FRAMES
                    else:
                        new_wizard_attack_cooldown -= 1
                    if new_o2 <= 0:
                        return replace(model,
                            player=replace(player, o2=0),
                            cycle=replace(cycle, death_reason="The wizard's blue bolts drained your oxygen", death_timer=0),
                            game=replace(game, frame=game.frame + 1, state="dead"),
                        ), []
                elif new_wise_outcome == "follow":
                    if game.frame % WISE_FOLLOW_STEP_FRAMES == 0:
                        next_wise = _pick_follower_tile(map_.tilemap, map_.wise_man, player.pos)
                        new_map = replace(map_, wise_man=next_wise)

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
                map=new_map,
                game=replace(game,
                    frame=game.frame + 1,
                    thought=new_thought,
                    wise_dialogue=new_wise_dialogue,
                    wise_options=new_wise_options,
                    wise_dialogue_active=new_wise_dialogue_active,
                    wise_dialogue_node=new_wise_dialogue_node,
                    wise_outcome=new_wise_outcome,
                    seen_memories=new_seen,
                    thought_cooldown=new_cooldown,
                    wise_dialogue_cooldown=new_wise_dialogue_cooldown,
                    wise_dialogue_index=new_wise_dialogue_index,
                    wizard_shots=new_wizard_shots,
                    wizard_attack_cooldown=new_wizard_attack_cooldown,
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
            wise_man = _find_wise_man_spot(tm, spawn)
            return replace(model,
                player=replace(player, pos=spawn, hydration=HYDRATION_START, hunger=HUNGER_START),
                map=Map(tilemap=tm, seed=s, spawn=spawn, wise_man=wise_man),
                cycle=replace(cycle, death_reason="", death_timer=0, rewind_timer=0, learned=()),
                game=replace(game,
                    state="play",
                    thought=None,
                    thought_cooldown=THOUGHT_INITIAL_DELAY,
                    wise_dialogue=None,
                    wise_options=None,
                    wise_dialogue_active=False,
                    wise_dialogue_node="",
                    wise_outcome="none",
                    wise_dialogue_cooldown=WISE_DIALOG_INITIAL_DELAY,
                    wise_dialogue_index=0,
                    wizard_shots=(),
                    wizard_attack_cooldown=0,
                ),
            ), []

        case ChooseWizardOption(option=o):
            if game.state != "play" or not game.wise_dialogue_active:
                return model, []
            if o not in (1, 2):
                return model, []
            node = WIZARD_DIALOGUE_TREE.get(game.wise_dialogue_node)
            if node is None:
                return model, []
            _, _, _, next_1, next_2 = node
            next_node = next_1 if o == 1 else next_2

            if next_node == "attack_end":
                final_text = "Then defend yourself. My staff speaks in blue lightning."
                duration = len(final_text) * WISE_DIALOG_CHAR_SPEED + WISE_DIALOG_READ_FRAMES
                return replace(model, game=replace(game,
                    wise_dialogue_active=False,
                    wise_dialogue_node="",
                    wise_options=None,
                    wise_outcome="attack",
                    wise_dialogue=NpcDialogueBubble(text=final_text, timer=0, duration=duration),
                    wise_dialogue_cooldown=WISE_DIALOG_COOLDOWN_FRAMES,
                    wizard_attack_cooldown=0,
                )), [PlayThoughtSound()]

            if next_node == "follow_end":
                final_text = "Wise choice. Stay close, and I will walk with you."
                duration = len(final_text) * WISE_DIALOG_CHAR_SPEED + WISE_DIALOG_READ_FRAMES
                return replace(model, game=replace(game,
                    wise_dialogue_active=False,
                    wise_dialogue_node="",
                    wise_options=None,
                    wise_outcome="follow",
                    wise_dialogue=NpcDialogueBubble(text=final_text, timer=0, duration=duration),
                    wise_dialogue_cooldown=WISE_DIALOG_COOLDOWN_FRAMES,
                )), [PlayThoughtSound()]

            if next_node not in WIZARD_DIALOGUE_TREE:
                return model, []
            text, option_1, option_2, _, _ = WIZARD_DIALOGUE_TREE[next_node]
            duration = len(text) * WISE_DIALOG_CHAR_SPEED + WISE_DIALOG_READ_FRAMES
            return replace(model, game=replace(game,
                wise_dialogue_active=True,
                wise_dialogue_node=next_node,
                wise_options=(option_1, option_2),
                wise_dialogue=NpcDialogueBubble(text=text, timer=0, duration=duration),
            )), [PlayThoughtSound()]

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
