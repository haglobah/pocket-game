"""init() and update(): pure game logic for title, overworld and screens."""

import math
import random
from dataclasses import replace

from . import dark, story
from .commands import Cmd, PlayMusic, PlaySound, RandomSeedText, StopMusic
from .common import aim, die, fpos, goto, learn, step, toward
from .constants import (
    BOLT_DAMAGE,
    BREATHE_GAIN,
    CHUNK,
    DEATH_CONFIRM_DELAY,
    DRINK_GAIN,
    DROWN_LOSS,
    EAT_GAIN,
    FOOD_MAX,
    GILL_DRAIN,
    LUNG_REFILL,
    MAP_H,
    MAP_W,
    O2_MAX,
    PLANTS,
    POISON_DRAIN,
    POISON_FRAMES,
    PORTAL,
    REWIND_FRAMES,
    SEED_CHARS,
    SEED_MAX,
    STEP_LAND,
    STEP_SPRINT,
    STEP_WATER,
    THOUGHT_CHAR_FRAMES,
    THOUGHT_COOLDOWN,
    THOUGHT_FIRST,
    THOUGHT_HOLD,
    WALKABLE,
    WATER_MAX,
    WIZARD_BOLT_EVERY,
    WIZARD_BOLT_RANGE,
    WIZARD_BOLT_SPEED,
    WIZARD_FOLLOW_EVERY,
    WIZARD_IDLE_EVERY,
    WIZARD_IDLE_START,
    WIZARD_LINE_HOLD,
    WIZARD_LISTEN_RANGE,
    WIZARD_RING,
    WIZARD_TALK_RANGE,
    Point,
)
from .mapgen import (
    chebyshev,
    generate,
    in_water,
    nearest,
    oasis_at,
    passable,
    seed_from_text,
    tile_at,
    wrap_delta,
    wrap_point,
)
from .messages import (
    Backspace,
    Breathe,
    Choose,
    Confirm,
    Drink,
    Eat,
    Msg,
    SeedChosen,
    Tick,
    ToggleBreath,
    ToggleMap,
    TypeChar,
)
from .model import Model, Player, Thought, Wizard


def init() -> tuple[Model, list[Cmd]]:
    return Model(), [PlayMusic("title")]


def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    if isinstance(msg, Tick):
        model = replace(model, frame=model.frame + 1, state_timer=model.state_timer + 1)
    match model.state:
        case "title":
            return _title(model, msg)
        case "play":
            return _play(model, msg)
        case "dead":
            return _dead(model, msg)
        case "rewind":
            return _rewind(model, msg)
        case "dark_play":
            return dark.update_dark(model, msg)
        case "ending_b":
            return _ending(model, msg)
    return model, []


# --- title ---------------------------------------------------------------


def _title(m: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case TypeChar(char=c) if c in SEED_CHARS and len(m.seed_text) < SEED_MAX:
            return replace(m, seed_text=m.seed_text + c), [PlaySound("blip")]
        case Backspace():
            return replace(m, seed_text=m.seed_text[:-1]), []
        case Confirm():
            if m.seed_text:
                return start_game(m.seed_text)
            return m, [RandomSeedText()]
        case SeedChosen(text=t):
            return start_game(t)
    return m, []


def start_game(text: str) -> tuple[Model, list[Cmd]]:
    seed = seed_from_text(text)
    m = Model(state="play", seed_text=text, seed=seed, world=generate(seed))
    return new_cycle(m, 1), [PlaySound("portal"), PlayMusic("main")]


def spawn_wizard(m: Model) -> Wizard:
    w = m.world
    rng = random.Random(w.seed * 31 + m.cycle)
    angle = rng.uniform(0, 2 * math.pi)
    dist = rng.uniform(*WIZARD_RING)
    guess = wrap_point(
        round(w.spawn.x + math.cos(angle) * dist),
        round(w.spawn.y + math.sin(angle) * dist),
    )
    pos = nearest(lambda x, y: tile_at(w, x, y) in WALKABLE, guess)
    return Wizard(pos=pos, prev=pos)


def new_cycle(m: Model, cycle: int) -> Model:
    spawn = m.world.spawn
    m = goto(
        m,
        "play",
        cycle=cycle,
        player=Player(pos=spawn, prev=spawn),
        learned=(),
        eaten=frozenset(),
        thought=None,
        thought_cd=THOUGHT_FIRST,
        bolts=(),
        dark=None,
        death_reason="",
    )
    return replace(m, wizard=spawn_wizard(m), explored=explore(m.explored, spawn))


def explore(explored: frozenset, p: Point) -> frozenset:
    cx, cy = p.x // CHUNK, p.y // CHUNK
    cw, ch = MAP_W // CHUNK, MAP_H // CHUNK
    around = {
        ((cx + i) % cw, (cy + j) % ch) for i in range(-2, 3) for j in range(-2, 3)
    }
    return explored if around <= explored else explored | around


# --- overworld -----------------------------------------------------------


def _play(m: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    p = m.player
    match msg:
        case Tick(dx=dx, dy=dy, sprint=sprint):
            return _tick(m, dx, dy, sprint)
        case ToggleBreath():
            if p.breath == "lungs":
                m = replace(m, player=replace(p, breath="gills"))
                return replace(m, learned=learn(m.learned, story.TO_GILLS)), [
                    PlaySound("toggle")
                ]
            m = replace(m, player=replace(p, breath="lungs"))
            return replace(m, learned=learn(m.learned, story.TO_LUNGS)), [
                PlaySound("toggle")
            ]
        case Breathe():
            if p.breath == "gills" and in_water(m.world, p.pos):
                o2 = min(O2_MAX, p.o2 + BREATHE_GAIN)
                m = replace(m, player=replace(p, o2=o2))
                return replace(m, learned=learn(m.learned, story.BREATHE_WATER)), [
                    PlaySound("breathe")
                ]
        case Drink():
            return _drink(m)
        case Eat():
            return _eat(m)
        case ToggleMap():
            return replace(m, show_map=not m.show_map), [PlaySound("toggle")]
        case Choose(option=o):
            return _choose(m, o)
    return m, []


def neighbors(p: Point):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            yield wrap_point(p.x + dx, p.y + dy)


def _drink(m: Model) -> tuple[Model, list[Cmd]]:
    p = m.player
    spot = next((n for n in neighbors(p.pos) if in_water(m.world, n)), None)
    if spot is None:
        return m, []
    oasis = oasis_at(m.world, spot)
    poison = POISON_FRAMES if oasis is not None and not oasis.safe else p.poison
    p = replace(p, water=min(WATER_MAX, p.water + DRINK_GAIN), poison=poison)
    m = replace(m, player=p, learned=learn(m.learned, story.DRINK))
    return m, [PlaySound("drink")]


def _eat(m: Model) -> tuple[Model, list[Cmd]]:
    p = m.player
    plant = next(
        (
            n
            for n in neighbors(p.pos)
            if tile_at(m.world, *n) in PLANTS and n not in m.eaten
        ),
        None,
    )
    if plant is None:
        return m, []
    p = replace(p, food=min(FOOD_MAX, p.food + EAT_GAIN))
    m = replace(
        m, player=p, eaten=m.eaten | {plant}, learned=learn(m.learned, story.EAT)
    )
    return m, [PlaySound("bite")]


def _choose(m: Model, option: int) -> tuple[Model, list[Cmd]]:
    w = m.wizard
    if (
        w is None
        or w.mode != "talk"
        or chebyshev(w.pos, m.player.pos) > WIZARD_LISTEN_RANGE
    ):
        return m, []
    _, options = story.DIALOGUE[w.node]
    nxt = options[option - 1][1]
    if nxt in story.DIALOGUE_END:
        w = replace(w, mode=nxt, line=story.DIALOGUE_END[nxt], line_age=0, timer=0)
    else:
        w = replace(w, node=nxt)
    return replace(m, wizard=w), [PlaySound("select")]


def _tick(m: Model, dx: int, dy: int, sprint: bool) -> tuple[Model, list[Cmd]]:
    world = m.world
    cmds: list[Cmd] = []

    def cost(t: Point) -> int:
        if in_water(world, t):
            return STEP_WATER
        return STEP_SPRINT if sprint else STEP_LAND

    def can_enter(t: Point) -> bool:
        return passable(world, t)

    p, moved = step(m.player, dx, dy, can_enter, cost)
    learned = m.learned
    explored = m.explored
    if moved:
        explored = explore(explored, p.pos)
        if in_water(world, p.pos):
            learned = learn(learned, story.SWIM)
            cmds.append(PlaySound("swim"))
        else:
            learned = learn(learned, story.WALK)
            if sprint:
                learned = learn(learned, story.SPRINT)
            cmds.append(PlaySound("step"))
    m = replace(m, player=p, learned=learned, explored=explored)

    if p.move_cd == 0 and tile_at(world, *p.pos) == PORTAL:
        return dark.enter_dark(m)

    p, reason = _survive(p, in_water(world, p.pos))
    m = replace(m, player=p)

    m, c = _wizard_tick(m)
    cmds += c
    m, c, bolt_kill = _bolts_tick(m)
    cmds += c
    m, c = _thought_tick(m)
    cmds += c

    if bolt_kill:
        reason = story.WIZARD_BOLTS
    if reason:
        m, c = die(m, reason)
        cmds += c
    return m, cmds


def _survive(p: Player, wet: bool) -> tuple[Player, str]:
    o2 = p.o2
    poison = p.poison
    poisoned = poison > 0
    if poisoned:
        o2 -= POISON_DRAIN
        poison -= 1
    underwater = p.underwater + 1 if wet else 0
    if p.breath == "lungs":
        if wet:
            if underwater % 60 == 0:
                o2 -= DROWN_LOSS
        else:
            o2 = min(O2_MAX, o2 + LUNG_REFILL)
    else:
        o2 -= GILL_DRAIN
    p = replace(
        p,
        o2=o2,
        poison=poison,
        underwater=underwater,
        water=p.water - 1,
        food=p.food - 1,
    )
    reason = ""
    if o2 <= 0:
        if poisoned:
            reason = story.POISONED
        elif p.breath == "lungs" and wet:
            reason = story.DROWNED
        elif p.breath == "gills":
            reason = story.GILLS_DRY
        else:
            reason = story.NO_O2
    elif p.water <= 0:
        reason = story.THIRST
    elif p.food <= 0:
        reason = story.HUNGER
    return p, reason


def _wizard_tick(m: Model) -> tuple[Model, list[Cmd]]:
    w = m.wizard
    if w is None:
        return m, []
    cmds: list[Cmd] = []
    p = m.player
    dist = chebyshev(w.pos, p.pos)
    w = replace(w, line_age=w.line_age + 1, timer=w.timer + 1, prev=w.pos)
    if w.line and w.line_age > WIZARD_LINE_HOLD:
        w = replace(w, line="")

    if w.mode == "idle":
        t = m.state_timer - WIZARD_IDLE_START
        if t >= 0 and t % WIZARD_IDLE_EVERY == 0:
            line = story.WIZARD_IDLE[w.idle_index % len(story.WIZARD_IDLE)]
            w = replace(w, line=line, line_age=0, idle_index=w.idle_index + 1)
            if dist <= 16:
                cmds.append(PlaySound("thought"))
        if dist <= WIZARD_TALK_RANGE:
            w = replace(w, mode="talk", node="opening", line="")
            cmds.append(PlaySound("thought"))
    elif w.mode == "follow":
        if w.timer % WIZARD_FOLLOW_EVERY == 0 and dist > 1:
            sx, sy = toward(w.pos, p.pos)
            for cx, cy in dict.fromkeys([(sx, sy), (sx, 0), (0, sy)]):
                t = wrap_point(w.pos.x + cx, w.pos.y + cy)
                if (cx or cy) and passable(m.world, t) and t != p.pos:
                    w = replace(w, pos=t)
                    break
    elif w.mode == "attack":
        if w.timer % WIZARD_BOLT_EVERY == 0 and dist <= WIZARD_BOLT_RANGE:
            px, py = fpos(p)
            bolt = aim(w.pos.x, w.pos.y, px, py, WIZARD_BOLT_SPEED, 90)
            m = replace(m, bolts=m.bolts + (bolt,))
            cmds.append(PlaySound("bolt"))
    return replace(m, wizard=w), cmds


def _bolts_tick(m: Model) -> tuple[Model, list[Cmd], bool]:
    if not m.bolts:
        return m, [], False
    px, py = fpos(m.player)
    kept = []
    hits = 0
    for b in m.bolts:
        b = replace(b, x=(b.x + b.vx) % MAP_W, y=(b.y + b.vy) % MAP_H, ttl=b.ttl - 1)
        if (
            abs(wrap_delta(b.x - px, MAP_W)) < 0.6
            and abs(wrap_delta(b.y - py, MAP_H)) < 0.6
        ):
            hits += 1
        elif b.ttl > 0:
            kept.append(b)
    m = replace(m, bolts=tuple(kept))
    if not hits:
        return m, [], False
    o2 = m.player.o2 - BOLT_DAMAGE * hits
    m = replace(m, player=replace(m.player, o2=o2))
    return m, [PlaySound("hit")], o2 <= 0


def _thought_tick(m: Model) -> tuple[Model, list[Cmd]]:
    t = m.thought
    if t is not None:
        t = replace(t, age=t.age + 1)
        if t.age > len(t.text) * THOUGHT_CHAR_FRAMES + THOUGHT_HOLD:
            return replace(m, thought=None, thought_cd=THOUGHT_COOLDOWN), []
        return replace(m, thought=t), []
    cd = max(0, m.thought_cd - 1)
    if cd > 0:
        return replace(m, thought_cd=cd), []
    for mem_id, eligible, text in story.MEMORIES:
        if mem_id not in m.seen and eligible(m.learned, m.cycle):
            m = replace(m, thought=Thought(mem_id, text), seen=m.seen | {mem_id})
            return replace(m, thought_cd=0), [PlaySound("thought")]
    return replace(m, thought_cd=cd), []


# --- screens -------------------------------------------------------------


def _dead(m: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick() if m.state_timer == DEATH_CONFIRM_DELAY:
            return m, [PlayMusic("death")]
        case Confirm() if m.state_timer >= DEATH_CONFIRM_DELAY:
            return goto(m, "rewind"), [StopMusic(), PlaySound("rewind")]
    return m, []


def _rewind(m: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick() if m.state_timer >= REWIND_FRAMES:
            return new_cycle(m, m.cycle + 1), [PlaySound("respawn"), PlayMusic("main")]
        case Tick() if m.state_timer % 30 == 0:
            return m, [PlaySound("tick")]
    return m, []


def _ending(m: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick() if m.state_timer == 150:
            return m, [PlayMusic("title")]
        case Confirm() if m.state_timer >= DEATH_CONFIRM_DELAY:
            return init()
    return m, []
