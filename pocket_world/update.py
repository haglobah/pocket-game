from dataclasses import replace

import math

from .constants import (
    MAP_W,
    MAP_H,
    Point,
    WATER,
    WATER_DEEP,
    PORTAL,
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
    PLAYER_MAX_HP,
    PUNCH_RANGE,
    PUNCH_COOLDOWN,
    INVINCIBLE_FRAMES,
    BOSS_FIRE_INTERVAL,
    PROJECTILE_SPEED,
    PROJECTILE_MOVE_INTERVAL,
    is_walkable,
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
    WISE_HELP_SHOT_SPEED,
    WISE_HELP_SHOT_TTL,
    WISE_HELP_ATTACK_COOLDOWN_FRAMES,
    WISE_HELP_DAMAGE,
    WISE_HELP_TARGET_RANGE,
    TILE_SIZE,
    WISE_ATTACK_O2_DAMAGE,
)
from .model import (
    Model, Map, PlantObject, ThoughtBubble, NpcDialogueBubble, WizardShot,
    BossPart, Boss, Projectile, Minion, DarkWorld,
)
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
    EnterDarkWorld,
    Punch,
    PlayerHit,
    BossPartDestroyed,
    BossDefeated,
    DarkWorldGenerated,
    DismissCredits,
    ChooseWizardOption,
)
from .commands import (
    Cmd, GenerateMap, PlayKilledByEnemySound, PlayStepSound, PlaySuffocatingSound, PlaySwimSound, PlayThoughtSound, PlayEatingSound,
    GenerateDarkWorld, PlayPunchSound, PlayHitSound, PlayBossFireSound, PlayVictorySound, PlayDrowningSound, PlayDehydrationSound, PlayStarvationSound,
)
from .commands import PlayMainThemeMusic, PlayDeathScreenMusic
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


# ---------------------------------------------------------------------------
# Wizard dialogue tree
# ---------------------------------------------------------------------------

WIZARD_DIALOGUE_TREE = {
    "opening": (
        "I have waited long for a visitor. Tell me — do you wish to survive this desert, or do you blame it for your suffering?",
        "I want to survive.",
        "This desert is a curse.",
        "survive_1",
        "blame_1",
    ),
    "survive_1": (
        "Survival demands trust. Will you walk with me, or walk alone?",
        "Walk with me.",
        "I walk alone.",
        "follow_end",
        "attack_end",
    ),
    "blame_1": (
        "Blame breeds enemies. Do you still seek a companion, or will you face me?",
        "I seek a companion.",
        "I will face you.",
        "follow_end",
        "attack_end",
    ),
}


def _start_wizard_dialogue(game):
    """Return a new Game fragment with the opening dialogue node staged."""
    node_key = "opening"
    text, option_1, option_2, _, _ = WIZARD_DIALOGUE_TREE[node_key]
    duration = len(text) * WISE_DIALOG_CHAR_SPEED + WISE_DIALOG_READ_FRAMES
    return replace(game,
        wise_dialogue_active=True,
        wise_dialogue_node=node_key,
        wise_options=(option_1, option_2),
        wise_dialogue=NpcDialogueBubble(text=text, timer=0, duration=duration),
    )


def _wizard_distance_tiles(player_pos: Point, wise_man: Point) -> float:
    dx = abs(player_pos.x - wise_man.x)
    dy = abs(player_pos.y - wise_man.y)
    return math.sqrt(dx * dx + dy * dy)


def _pick_follower_tile(tilemap, current: Point, target: Point) -> Point:
    """Move one step toward target on walkable tiles."""
    dx = target.x - current.x
    dy = target.y - current.y
    sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
    candidates = []
    if sx != 0 and sy != 0:
        candidates.append(Point(current.x + sx, current.y + sy))
    if sx != 0:
        candidates.append(Point(current.x + sx, current.y))
    if sy != 0:
        candidates.append(Point(current.x, current.y + sy))
    for p in candidates:
        if 0 <= p.x < MAP_W and 0 <= p.y < MAP_H and is_walkable(tilemap[p.y][p.x]):
            return p
    return current


def _spawn_wizard_shot(origin: Point, target_pos: Point) -> WizardShot:
    """Spawn a hostile wizard projectile (pixel-based coords)."""
    ox = origin.x * TILE_SIZE + TILE_SIZE // 2
    oy = origin.y * TILE_SIZE + TILE_SIZE // 2
    tx = target_pos.x * TILE_SIZE + TILE_SIZE // 2
    ty = target_pos.y * TILE_SIZE + TILE_SIZE // 2
    dx = tx - ox
    dy = ty - oy
    dist = max(1.0, math.sqrt(dx * dx + dy * dy))
    vx = dx / dist * WISE_ATTACK_SHOT_SPEED
    vy = dy / dist * WISE_ATTACK_SHOT_SPEED
    return WizardShot(x=float(ox), y=float(oy), vx=vx, vy=vy, ttl=WISE_ATTACK_SHOT_TTL)


def _spawn_dark_wizard_shot(origin: Point, target: Point) -> WizardShot:
    """Spawn a friendly wizard projectile (tile-based float coords)."""
    ox = origin.x + 0.5
    oy = origin.y + 0.5
    tx = target.x + 0.5
    ty = target.y + 0.5
    dx = tx - ox
    dy = ty - oy
    dist = max(0.01, math.sqrt(dx * dx + dy * dy))
    vx = dx / dist * WISE_HELP_SHOT_SPEED
    vy = dy / dist * WISE_HELP_SHOT_SPEED
    return WizardShot(x=ox, y=oy, vx=vx, vy=vy, ttl=WISE_HELP_SHOT_TTL)


def _find_dark_wizard_spawn(tilemap, player_pos: Point) -> Point:
    """Find a walkable tile near player for wizard companion in dark world."""
    for r in range(1, 6):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                nx, ny = player_pos.x + dx, player_pos.y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and is_walkable(tilemap[ny][nx]):
                    return Point(nx, ny)
    return Point(player_pos.x + 2, player_pos.y + 2)


def _pick_dark_wizard_target(wizard_pos: Point, boss_parts: tuple, minions: tuple) -> Point | None:
    """Pick the closest enemy within range for the friendly wizard to shoot."""
    best = None
    best_dist = WISE_HELP_TARGET_RANGE + 1
    for m in minions:
        if m.hp <= 0:
            continue
        d = abs(m.pos.x - wizard_pos.x) + abs(m.pos.y - wizard_pos.y)
        if d < best_dist:
            best_dist = d
            best = m.pos
    for part in boss_parts:
        if part.hp <= 0:
            continue
        cx = part.pos.x + part.size.x // 2
        cy = part.pos.y + part.size.y // 2
        d = abs(cx - wizard_pos.x) + abs(cy - wizard_pos.y)
        if d < best_dist:
            best_dist = d
            best = Point(cx, cy)
    return best


def _advance_wizard_shots(shots: tuple[WizardShot, ...], player_pos: Point) -> tuple[tuple[WizardShot, ...], int]:
    """Advance hostile wizard shots and return (remaining_shots, total_damage)."""
    alive = []
    damage = 0
    px = player_pos.x * TILE_SIZE + TILE_SIZE // 2
    py = player_pos.y * TILE_SIZE + TILE_SIZE // 2
    for shot in shots:
        nx = shot.x + shot.vx
        ny = shot.y + shot.vy
        ttl = shot.ttl - 1
        if ttl <= 0:
            continue
        if abs(nx - px) < TILE_SIZE and abs(ny - py) < TILE_SIZE:
            damage += WISE_ATTACK_O2_DAMAGE
            continue
        alive.append(replace(shot, x=nx, y=ny, ttl=ttl))
    return tuple(alive), damage


def _find_wise_man_spot(
    tilemap: tuple[tuple[int, ...], ...],
    spawn: Point,
    min_r: int = WISE_SPAWN_MIN_DISTANCE,
    max_r: int = WISE_SPAWN_MAX_DISTANCE,
) -> Point:
    """Find a walkable tile for the wise man between min_r and max_r from spawn."""
    for r in range(min_r, max_r + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                nx, ny = spawn.x + dx, spawn.y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and is_walkable(tilemap[ny][nx]):
                    return Point(nx, ny)
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
            if game.state == "dark_play":
                return _dark_tick(model)
            if game.state == "dead":
                return replace(model,
                    cycle=replace(cycle, death_timer=cycle.death_timer + 1),
                    game=replace(game, frame=game.frame + 1),
                ), []
            new_o2 = player.o2
            new_poison = player.poison_timer
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
                # Poison drain: suffocate over 10 seconds
                new_poison = max(0, player.poison_timer - 1) if player.poison_timer > 0 else 0
                if new_poison > 0:
                    new_o2 = max(0, new_o2 - POISON_O2_DRAIN)
                # Check for O2 death
                if new_o2 <= 0:
                    if new_poison > 0 or (player.poison_timer > 0 and new_poison == 0):
                        reason = "Suffocated from poisoned water"
                        cmd = PlaySuffocatingSound()
                    elif player.breathing_mode == LUNGS and underwater:
                        reason = "Drowned (lungs underwater)"
                        cmd = PlayDrowningSound()
                    elif player.breathing_mode == GILLS:
                        reason = "Suffocated (gills ran dry)"
                        cmd = PlaySuffocatingSound()
                    else:
                        reason = "Ran out of oxygen"
                        cmd = PlaySuffocatingSound()
                    new_model, cmds = transition_to_death(model, reason)
                    return new_model, cmds + [cmd]
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
                        ), [PlaySuffocatingSound()]
                elif new_wise_outcome == "follow":
                    if game.frame % WISE_FOLLOW_STEP_FRAMES == 0:
                        next_wise = _pick_follower_tile(map_.tilemap, map_.wise_man, player.pos)
                        new_map = replace(map_, wise_man=next_wise)

            # Deplete hydration and hunger
            new_hydration = max(0, player.hydration - HYDRATION_DEPLETION)
            new_hunger = max(0, player.hunger - HUNGER_DEPLETION)
            if game.state == "play":
                if new_hydration <= 0:
                    return transition_to_death(model, "Died of dehydration"), [PlayDehydrationSound()]
                if new_hunger <= 0:
                    return transition_to_death(model, "Died of starvation"), [PlayStarvationSound()]
            return replace(model,
                player=replace(player,
                    move_timer=max(0, player.move_timer - 1),
                    o2=new_o2,
                    hydration=new_hydration,
                    hunger=new_hunger,
                    poison_timer=new_poison,
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
            if game.state == "dark_play":
                return _dark_move(model, d)
            if game.state != "play":
                return model, []
            if player.move_timer > 0:
                return replace(model, player=replace(player, facing=d)), []
            raw = Point(player.pos.x + d.x, player.pos.y + d.y)
            new_pos = Point(raw.x % MAP_W, raw.y % MAP_H)
            tile = map_.tilemap[new_pos.y][new_pos.x]
            if tile == PORTAL:
                return replace(model,
                    player=replace(player, pos=new_pos, facing=d, move_timer=MOVE_DELAY_LAND),
                ), [GenerateDarkWorld(seed=map_.seed, tilemap=map_.tilemap)]
            if map_.has_object_at(new_pos):
                return replace(model, player=replace(player, facing=d, move_timer=0)), []
            if is_walkable(tile):
                delay = MOVE_DELAY_RUNNING if player.sprinting else MOVE_DELAY_LAND
                skill = "sprinting" if player.sprinting else "walking on land"
                return replace(model,
                    player=replace(player, pos=new_pos, facing=d, move_timer=delay),
                    cycle=replace(cycle, learned=_add_learned(cycle, skill)),
                ), [PlayStepSound()]
            if is_swimmable(tile):
                return replace(model,
                    player=replace(player, pos=new_pos, facing=d, move_timer=MOVE_DELAY_WATER),
                    cycle=replace(cycle, learned=_add_learned(cycle, "swimming")),
                ), [PlaySwimSound()]
            return replace(model, player=replace(player, facing=d, move_timer=0)), []

        case StartGame(seed=s):
            return model, [GenerateMap(seed=s)]

        case MapGenerated(tilemap=tm, seed=s, objects=objs, poison_water=pw):
            spawn = _find_spawn(tm, objs)
            wise_man = _find_wise_man_spot(tm, spawn)
            return replace(model,
                player=replace(player, pos=spawn, hydration=HYDRATION_START, hunger=HUNGER_START, poison_timer=0),
                map=Map(
                    tilemap=tm,
                    seed=s,
                    wise_man=wise_man,
                    objects=objs,
                    poison_water=pw,
                ),
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
            ), [PlayMainThemeMusic()]

        case TypeChar(char=c):
            if game.state == "title" and len(game.seed_input) < 16:
                return replace(model, game=replace(game, seed_input=game.seed_input + c)), []
            return model, []

        case Backspace():
            if game.state == "title" and game.seed_input:
                return replace(model, game=replace(game, seed_input=game.seed_input[:-1])), []
            return model, []

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

        case DarkWorldGenerated(boss_parts=bp, minions=mn):
            parts = tuple(
                BossPart(name=name, hp=hp, max_hp=mhp, pos=pos, size=size)
                for name, hp, mhp, pos, size in bp
            )
            minions = tuple(
                Minion(kind=kind, pos=pos, hp=hp, facing=DOWN, move_timer=md)
                for kind, pos, hp, md in mn
            )
            dark = DarkWorld(
                boss=Boss(parts=parts, fire_timer=BOSS_FIRE_INTERVAL, phase="active"),
                minions=minions,
                projectiles=(),
                arena_tiles=model.map.tilemap,
                wizard_pos=_find_dark_wizard_spawn(model.map.tilemap, player.pos) if game.wise_outcome == "follow" else None,
            )
            return replace(model,
                player=replace(player, hp=PLAYER_MAX_HP, invincible_timer=0, punch_timer=0),
                dark_world=dark,
                game=replace(game, state="dark_play"),
            ), []

        case Punch():
            if game.state != "dark_play" or model.dark_world is None:
                return model, []
            if player.punch_timer > 0:
                return model, []
            dw = model.dark_world
            cmds: list[Cmd] = [PlayPunchSound()]
            new_parts = list(dw.boss.parts)
            for i, part in enumerate(new_parts):
                if part.hp <= 0:
                    continue
                if _punch_hits_rect(player.pos, player.facing, part.pos, part.size):
                    new_hp = part.hp - 1
                    new_parts[i] = replace(part, hp=new_hp)
            new_minions = list(dw.minions)
            for i, m in enumerate(new_minions):
                if m.hp <= 0:
                    continue
                if _punch_hits_point(player.pos, player.facing, m.pos):
                    new_minions[i] = replace(m, hp=m.hp - 1)
            alive_parts = [p for p in new_parts if p.hp > 0]
            alive_minions = tuple(m for m in new_minions if m.hp > 0)
            new_boss = replace(dw.boss, parts=tuple(new_parts))
            if not alive_parts:
                new_boss = replace(new_boss, phase="defeated")
                return replace(model,
                    player=replace(player, punch_timer=PUNCH_COOLDOWN),
                    dark_world=replace(dw, boss=new_boss, minions=alive_minions),
                    game=replace(game, state="ending_b"),
                ), cmds + [PlayVictorySound()]
            return replace(model,
                player=replace(player, punch_timer=PUNCH_COOLDOWN),
                dark_world=replace(dw, boss=new_boss, minions=alive_minions),
            ), cmds

        case BossDefeated():
            return replace(model, game=replace(game, state="ending_b")), [PlayVictorySound()]

        case DismissCredits():
            from .model import init as model_init
            return model_init()

    return model, []


# ---------------------------------------------------------------------------
# Dark Pocket World helpers
# ---------------------------------------------------------------------------

def _dark_move(model: Model, d: Point) -> tuple[Model, list[Cmd]]:
    """Handle movement inside the dark world (same map, dark sprites)."""
    player = model.player
    if player.move_timer > 0:
        return replace(model, player=replace(player, facing=d)), []
    raw = Point(player.pos.x + d.x, player.pos.y + d.y)
    if raw.x < 0 or raw.x >= MAP_W or raw.y < 0 or raw.y >= MAP_H:
        return replace(model, player=replace(player, facing=d)), []
    if not is_walkable(model.map.tilemap[raw.y][raw.x]):
        return replace(model, player=replace(player, facing=d)), []
    delay = MOVE_DELAY_RUNNING if player.sprinting else MOVE_DELAY_LAND
    return replace(model,
        player=replace(player, pos=raw, facing=d, move_timer=delay),
    ), [PlayStepSound()]


def _dark_tick(model: Model) -> tuple[Model, list[Cmd]]:
    """Per-frame update for the dark_play state."""
    player = model.player
    dw = model.dark_world
    game = model.game
    if dw is None:
        return model, []

    cmds: list[Cmd] = []

    new_invincible = max(0, player.invincible_timer - 1)
    new_punch_timer = max(0, player.punch_timer - 1)
    new_move_timer = max(0, player.move_timer - 1)
    new_hp = player.hp

    # --- Boss AI: fire projectiles from all alive parts ---
    boss = dw.boss
    new_fire_timer = boss.fire_timer - 1
    new_projectiles = list(dw.projectiles)
    new_tick = dw.tick + 1
    new_wizard_pos = dw.wizard_pos
    new_wizard_shots = list(dw.wizard_shots)
    new_wizard_attack_cooldown = max(0, dw.wizard_attack_cooldown - 1)
    new_wizard_follow_timer = dw.wizard_follow_timer + 1

    if new_fire_timer <= 0 and boss.phase == "active":
        head = next((p for p in boss.parts if p.name == "head" and p.hp > 0), None)
        if head:
            src = Point(head.pos.x + head.size.x // 2,
                        head.pos.y + head.size.y // 2)
            dx = player.pos.x - src.x
            dy = player.pos.y - src.y
            dist = max(1, math.sqrt(dx * dx + dy * dy))
            vx = round(dx / dist * PROJECTILE_SPEED)
            vy = round(dy / dist * PROJECTILE_SPEED)
            if vx == 0 and vy == 0:
                vy = PROJECTILE_SPEED
            new_projectiles.append(Projectile(pos=src, velocity=Point(vx, vy)))
            cmds.append(PlayBossFireSound())
        new_fire_timer = BOSS_FIRE_INTERVAL

    # --- Update projectiles (only move every PROJECTILE_MOVE_INTERVAL frames) ---
    updated_projectiles = []
    should_move = (new_tick % PROJECTILE_MOVE_INTERVAL == 0)
    for proj in new_projectiles:
        if should_move:
            np_ = Point(proj.pos.x + proj.velocity.x, proj.pos.y + proj.velocity.y)
            if np_.x < 0 or np_.x >= MAP_W or np_.y < 0 or np_.y >= MAP_H:
                continue
            if abs(np_.x - player.pos.x) <= 1 and abs(np_.y - player.pos.y) <= 1:
                if new_invincible == 0:
                    new_hp -= 1
                    new_invincible = INVINCIBLE_FRAMES
                    cmds.append(PlayHitSound())
                continue
            updated_projectiles.append(replace(proj, pos=np_))
        else:
            if abs(proj.pos.x - player.pos.x) <= 1 and abs(proj.pos.y - player.pos.y) <= 1:
                if new_invincible == 0:
                    new_hp -= 1
                    new_invincible = INVINCIBLE_FRAMES
                    cmds.append(PlayHitSound())
                continue
            updated_projectiles.append(proj)

    # --- Minion AI ---
    new_minions = []
    for m in dw.minions:
        if m.hp <= 0:
            continue
        mt = m.move_timer - 1
        if mt <= 0:
            dx = player.pos.x - m.pos.x
            dy = player.pos.y - m.pos.y
            sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
            sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
            new_mpos = Point(m.pos.x + sx, m.pos.y + sy)
            if (new_mpos.x < 0 or new_mpos.x >= MAP_W or
                    new_mpos.y < 0 or new_mpos.y >= MAP_H or
                    not is_walkable(model.map.tilemap[new_mpos.y][new_mpos.x])):
                new_mpos = m.pos
            new_facing = Point(sx if sx != 0 else m.facing.x, sy if sy != 0 else m.facing.y)
            mt = _minion_delay(m.kind)
            new_minions.append(replace(m, pos=new_mpos, facing=new_facing, move_timer=mt))
            if abs(new_mpos.x - player.pos.x) <= 1 and abs(new_mpos.y - player.pos.y) <= 1:
                if new_invincible == 0:
                    new_hp -= 1
                    new_invincible = INVINCIBLE_FRAMES
                    cmds.append(PlayHitSound())
        else:
            new_minions.append(replace(m, move_timer=mt))

    # --- Friendly wizard companion AI ---
    if new_wizard_pos is not None:
        if new_wizard_follow_timer >= WISE_FOLLOW_STEP_FRAMES:
            new_wizard_pos = _pick_follower_tile(model.map.tilemap, new_wizard_pos, player.pos)
            new_wizard_follow_timer = 0

        target = _pick_dark_wizard_target(new_wizard_pos, boss.parts, tuple(new_minions))
        if target is not None and new_wizard_attack_cooldown == 0:
            new_wizard_shots.append(_spawn_dark_wizard_shot(new_wizard_pos, target))
            new_wizard_attack_cooldown = WISE_HELP_ATTACK_COOLDOWN_FRAMES

    # --- Friendly wizard shots: damage minions and boss parts ---
    updated_wizard_shots: list[WizardShot] = []
    minion_list = list(new_minions)
    boss_parts = list(boss.parts)
    for shot in new_wizard_shots:
        nx = shot.x + shot.vx
        ny = shot.y + shot.vy
        ttl = shot.ttl - 1
        if ttl <= 0:
            continue

        hit = False
        for i, m in enumerate(minion_list):
            if m.hp <= 0:
                continue
            if abs(nx - (m.pos.x + 0.5)) <= 0.55 and abs(ny - (m.pos.y + 0.5)) <= 0.55:
                minion_list[i] = replace(m, hp=max(0, m.hp - WISE_HELP_DAMAGE))
                hit = True
                break

        if not hit:
            for i, part in enumerate(boss_parts):
                if part.hp <= 0:
                    continue
                if (
                    part.pos.x <= nx <= part.pos.x + part.size.x
                    and part.pos.y <= ny <= part.pos.y + part.size.y
                ):
                    boss_parts[i] = replace(part, hp=max(0, part.hp - WISE_HELP_DAMAGE))
                    hit = True
                    break

        if not hit:
            updated_wizard_shots.append(replace(shot, x=nx, y=ny, ttl=ttl))

    new_minions = [m for m in minion_list if m.hp > 0]
    new_boss_parts = tuple(boss_parts)
    alive_parts = [p for p in new_boss_parts if p.hp > 0]
    if boss.phase == "active" and not alive_parts:
        return replace(model,
            player=replace(player,
                hp=new_hp,
                invincible_timer=new_invincible,
                punch_timer=new_punch_timer,
                move_timer=new_move_timer,
            ),
            dark_world=replace(dw,
                boss=replace(boss, parts=new_boss_parts, phase="defeated", fire_timer=new_fire_timer),
                minions=tuple(new_minions),
                projectiles=tuple(updated_projectiles),
                wizard_pos=new_wizard_pos,
                wizard_shots=tuple(updated_wizard_shots),
                wizard_attack_cooldown=new_wizard_attack_cooldown,
                wizard_follow_timer=new_wizard_follow_timer,
                tick=new_tick,
            ),
            game=replace(game, state="ending_b", frame=game.frame + 1),
        ), cmds + [PlayVictorySound()]

    # --- Check death ---
    if new_hp <= 0:
        return replace(model,
            player=replace(player, hp=0),
            cycle=replace(model.cycle, death_reason="Defeated in the Dark Pocket World", death_timer=0),
            game=replace(game, state="dead", frame=game.frame + 1),
        ), cmds + [PlayKilledByEnemySound()]

    new_boss = replace(boss, fire_timer=new_fire_timer, parts=new_boss_parts)
    new_dw = replace(dw,
        boss=new_boss,
        minions=tuple(new_minions),
        projectiles=tuple(updated_projectiles),
        wizard_pos=new_wizard_pos,
        wizard_shots=tuple(updated_wizard_shots),
        wizard_attack_cooldown=new_wizard_attack_cooldown,
        wizard_follow_timer=new_wizard_follow_timer,
        tick=new_tick,
    )
    return replace(model,
        player=replace(player,
            hp=new_hp,
            invincible_timer=new_invincible,
            punch_timer=new_punch_timer,
            move_timer=new_move_timer,
        ),
        dark_world=new_dw,
        game=replace(game, frame=game.frame + 1),
    ), cmds


def _minion_delay(kind: str) -> int:
    delays = {"squid": 45, "squid_small": 35, "scorpion": 55, "golem": 70}
    return delays.get(kind, 45)


def _punch_hits_rect(player_pos: Point, facing: Point, rect_pos: Point, rect_size: Point) -> bool:
    """Check if punch in facing direction hits a rectangular area."""
    for i in range(1, PUNCH_RANGE + 1):
        px = player_pos.x + facing.x * i
        py = player_pos.y + facing.y * i
        if (rect_pos.x <= px < rect_pos.x + rect_size.x and
                rect_pos.y <= py < rect_pos.y + rect_size.y):
            return True
    return False


def _punch_hits_point(player_pos: Point, facing: Point, target: Point) -> bool:
    """Check if punch in facing direction hits a single-tile target."""
    for i in range(1, PUNCH_RANGE + 1):
        px = player_pos.x + facing.x * i
        py = player_pos.y + facing.y * i
        if abs(px - target.x) <= 1 and abs(py - target.y) <= 1:
            return True
    return False
