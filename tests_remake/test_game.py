from dataclasses import replace

from pocket_remake.commands import PlayMusic, PlaySound, RandomSeedText
from pocket_remake.constants import (
    BREATHE_GAIN,
    CACTUS,
    DRINK_GAIN,
    EAT_GAIN,
    FOOD_START,
    O2_MAX,
    PALM,
    PORTAL,
    SPAWN_CLEAR,
    WATER_START,
    Point,
)
from pocket_remake.dark import ARENA_START, BossPart, Minion
from pocket_remake.mapgen import (
    distance,
    generate,
    passable,
    seed_from_text,
    tile_at,
)
from pocket_remake.messages import (
    Backspace,
    Breathe,
    Choose,
    Confirm,
    Drink,
    Eat,
    Punch,
    SeedChosen,
    Tick,
    ToggleBreath,
    TypeChar,
)
from pocket_remake.update import init, update


def start(text="abc"):
    m, _ = init()
    for c in text:
        m, _ = update(m, TypeChar(c))
    m, _ = update(m, Confirm())
    return m


def run(m, n, **held):
    cmds = []
    for _ in range(n):
        m, c = update(m, Tick(**held))
        cmds += c
    return m, cmds


def place(m, p):
    return replace(m, player=replace(m.player, pos=p, prev=p))


def without_wizard(m):
    return replace(m, wizard=None)


# --- title ---------------------------------------------------------------


def test_title_accepts_seed_chars_up_to_16():
    m, cmds = init()
    assert m.state == "title"
    assert PlayMusic("title") in cmds
    for c in "a1!" + "x" * 20:
        m, _ = update(m, TypeChar(c))
    assert m.seed_text == "a1" + "x" * 14
    m, _ = update(m, Backspace())
    assert m.seed_text == "a1" + "x" * 13


def test_seed_text_is_md5_hashed():
    m = start("abc")
    assert m.state == "play"
    assert m.seed == seed_from_text("abc")
    assert m.cycle == 1


def test_empty_seed_asks_for_random_one():
    m, _ = init()
    m, cmds = update(m, Confirm())
    assert cmds == [RandomSeedText()]
    m, _ = update(m, SeedChosen("q7"))
    assert m.state == "play" and m.seed_text == "q7"


# --- world ---------------------------------------------------------------


def test_world_layout_rules():
    for text in ["abc", "pocket", "42"]:
        w = generate(seed_from_text(text))
        assert passable(w, w.spawn)
        assert len(w.oases) == 3
        assert sorted(o.kind for o in w.oases) == ["green", "red", "yellow"]
        for o in w.oases:
            assert 85 <= distance(o.center, w.spawn) <= 110
            for other in w.oases:
                if other is not o:
                    assert distance(o.center, other.center) >= 50
        assert tile_at(w, *w.portal) == PORTAL
        for y in range(-75, 76, 3):
            for x in range(-75, 76, 3):
                if x * x + y * y < SPAWN_CLEAR**2:
                    t = tile_at(w, w.spawn.x + x, w.spawn.y + y)
                    assert t not in (PALM, CACTUS)


def test_same_seed_same_world():
    assert generate(5) == generate(5)


# --- breathing -----------------------------------------------------------


def water_spot(m, kind="green"):
    return next(o.center for o in m.world.oases if o.kind == kind)


def test_lungs_refill_on_land():
    m = without_wizard(start())
    m = replace(m, player=replace(m.player, o2=100))
    m, _ = run(m, 10)
    assert m.player.o2 == 140


def test_lungs_underwater_drown():
    m = without_wizard(place(start(), water_spot(start())))
    m, _ = run(m, 60)
    assert m.player.o2 == O2_MAX - 180
    m, _ = run(m, 359)
    assert m.state == "play"
    m, _ = run(m, 1)
    assert m.state == "dead"
    assert m.death_reason == "Drowned (lungs underwater)"


def test_gills_drain_and_breathe_underwater():
    m = without_wizard(start())
    m, _ = update(m, ToggleBreath())
    assert m.player.breath == "gills"
    assert "switching to gills" in m.learned
    m, _ = run(m, 700)
    assert m.player.o2 == O2_MAX - 700
    m, _ = update(m, Breathe())  # on land: nothing
    assert m.player.o2 == O2_MAX - 700
    m = place(m, water_spot(m))
    m, _ = update(m, Breathe())
    assert m.player.o2 == O2_MAX - 700 + BREATHE_GAIN
    assert "breathing underwater" in m.learned


def test_gills_run_dry():
    m = without_wizard(start())
    m, _ = update(m, ToggleBreath())
    m, _ = run(m, O2_MAX)
    assert m.state == "dead"
    assert m.death_reason == "Suffocated (gills ran dry)"


# --- needs ---------------------------------------------------------------


def test_dehydration():
    m = without_wizard(start())
    m, _ = run(m, WATER_START - 1)
    assert m.state == "play"
    m, _ = run(m, 1)
    assert m.death_reason == "Died of dehydration"


def test_starvation():
    m = without_wizard(start())
    m = replace(m, player=replace(m.player, water=10**9))
    m, _ = run(m, FOOD_START)
    assert m.death_reason == "Died of starvation"


def test_drink_safe_water():
    m = without_wizard(start())
    m = place(m, water_spot(m, "green"))
    m, _ = update(m, Drink())
    assert m.player.water == WATER_START + DRINK_GAIN
    assert m.player.poison == 0
    assert "drinking water" in m.learned


def test_drink_needs_water_nearby():
    m = without_wizard(start())
    m, _ = update(m, Drink())
    assert m.player.water == WATER_START


def test_poisoned_water_kills():
    m = without_wizard(start())
    m = place(m, water_spot(m, "red"))
    m, _ = update(m, Drink())
    assert m.player.poison > 0
    m = place(m, m.world.spawn)
    m, _ = run(m, 10)
    assert m.player.o2 == O2_MAX - 20  # +4 lungs, -6 poison
    m, _ = run(m, 600)
    assert m.death_reason == "Suffocated from poisoned water"


def find_plant(m):
    w = m.world
    for o in w.oases:
        for dy in range(-14, 15):
            for dx in range(-14, 15):
                p = Point(o.center.x + dx, o.center.y + dy)
                if tile_at(w, *p) in (PALM, CACTUS):
                    for nx, ny in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        n = Point(p.x + nx, p.y + ny)
                        if passable(w, n):
                            return p, n
    raise AssertionError("no plant")


def test_eat_once_per_plant():
    m = without_wizard(start())
    plant, stand = find_plant(m)
    m = place(m, stand)
    m, cmds = update(m, Eat())
    assert m.player.food == FOOD_START + EAT_GAIN
    assert plant in m.eaten
    assert PlaySound("bite") in cmds
    m, _ = update(m, Eat())
    assert m.player.food == FOOD_START + EAT_GAIN


# --- movement and learning -----------------------------------------------


def test_walking_steps_every_8_frames_and_is_learned():
    m = without_wizard(start())
    p0 = m.player.pos
    m, _ = run(m, 1, dx=0, dy=1)
    assert m.player.pos == Point(p0.x, p0.y + 1)
    assert m.learned == ("walking on land",)
    m, _ = run(m, 7, dx=0, dy=1)
    assert m.player.pos == Point(p0.x, p0.y + 1)
    m, _ = run(m, 1, dx=0, dy=1)
    assert m.player.pos == Point(p0.x, p0.y + 2)


def test_sprint_is_faster():
    m = without_wizard(start())
    p0 = m.player.pos
    m, _ = run(m, 9, dx=0, dy=1, sprint=True)
    assert m.player.pos == Point(p0.x, p0.y + 3)
    assert "sprinting" in m.learned


# --- thoughts ------------------------------------------------------------


def test_first_thought_after_3_seconds_once_per_game():
    m = without_wizard(start())
    m, _ = run(m, 179)
    assert m.thought is None
    m, cmds = run(m, 1)
    assert m.thought.text == "Where... am I?"
    assert PlaySound("thought") in cmds
    assert "awakening" in m.seen


# --- cycles --------------------------------------------------------------


def test_death_rewind_next_cycle():
    m = without_wizard(start())
    m, _ = update(m, ToggleBreath())
    m, _ = run(m, O2_MAX)
    assert m.state == "dead"
    m, _ = update(m, Confirm())
    assert m.state == "dead"  # too early
    m, _ = run(m, 60)
    m, _ = update(m, Confirm())
    assert m.state == "rewind"
    m, _ = run(m, 180)
    assert m.state == "play"
    assert m.cycle == 2
    assert m.learned == ()
    assert m.player.pos == m.world.spawn
    assert "awakening" in m.seen  # memories survive the rewind


def test_second_cycle_remembers_the_machine():
    m = without_wizard(start())
    m = replace(m, seen=frozenset({"awakening"}))
    m, _ = update(m, ToggleBreath())
    m, _ = run(m, O2_MAX + 60)
    m, _ = update(m, Confirm())
    m, _ = run(m, 180)
    m = without_wizard(m)
    m, _ = run(m, 180)
    assert m.thought.id == "machine"


# --- wizard --------------------------------------------------------------


def next_to_wizard(m):
    w = m.wizard.pos
    return place(m, Point(w.x + 1, w.y))


def test_wizard_dialogue_to_follow():
    m = next_to_wizard(start())
    m, _ = run(m, 1)
    assert m.wizard.mode == "talk" and m.wizard.node == "opening"
    m, _ = update(m, Choose(1))
    assert m.wizard.node == "survive_1"
    m, _ = update(m, Choose(1))
    assert m.wizard.mode == "follow"


def test_wizard_dialogue_to_attack():
    m = next_to_wizard(start())
    m, _ = run(m, 1)
    m, _ = update(m, Choose(2))
    assert m.wizard.node == "blame_1"
    m, _ = update(m, Choose(2))
    assert m.wizard.mode == "attack"
    m, cmds = run(m, 24)
    assert PlaySound("bolt") in cmds
    m, _ = run(m, 30)
    assert m.player.o2 < O2_MAX


# --- dark world ----------------------------------------------------------


def enter_dark(m):
    m = place(without_wizard(m), m.world.portal)
    m, cmds = run(m, 1)
    assert m.state == "dark_play"
    assert PlayMusic("boss") in cmds
    return m


def test_portal_leads_to_dark_world():
    m = enter_dark(start())
    assert m.player.pos == ARENA_START
    assert m.dark.hp == 5
    assert len(m.dark.minions) == 9
    assert {p.name for p in m.dark.parts} == {"head", "wings", "left_arm", "right_arm"}


def set_parts(m, **hp):
    parts = tuple(replace(p, hp=hp.get(p.name, p.hp)) for p in m.dark.parts)
    return replace(m, dark=replace(m.dark, parts=parts, minions=()))


def facing_part(m, name):
    part = next(p for p in m.dark.parts if p.name == name)
    stand = Point(part.x, part.y + part.h)
    return replace(
        m, player=replace(m.player, pos=stand, prev=stand, facing=Point(0, -1))
    )


def test_head_is_shielded_while_arms_live():
    m = facing_part(set_parts(enter_dark(start())), "head")
    m, cmds = update(m, Punch())
    head = next(p for p in m.dark.parts if p.name == "head")
    assert head.hp == head.max_hp
    assert PlaySound("tink") in cmds


def test_destroying_last_part_wins():
    m = set_parts(enter_dark(start()), head=0, wings=0, left_arm=0, right_arm=1)
    m = facing_part(m, "right_arm")
    m, _ = update(m, Punch())
    m, _ = run(m, 1)
    assert m.state == "ending_b"
    m, _ = run(m, 60)
    m, _ = update(m, Confirm())
    assert m.state == "title" and m.seed_text == ""


def test_dark_world_defeat():
    m = enter_dark(start())
    p = m.player.pos
    minion = Minion("squid", Point(p.x + 1, p.y), Point(p.x + 1, p.y), 2, 1)
    m = replace(m, dark=replace(m.dark, hp=1, minions=(minion,), shots=()))
    m, _ = run(m, 1)
    assert m.state == "dead"
    assert m.death_reason == "Defeated in the Dark Pocket World"


def test_punch_kills_minion():
    m = enter_dark(start())
    p = m.player.pos
    minion = Minion("squid_small", Point(p.x, p.y - 2), Point(p.x, p.y - 2), 1, 99)
    m = replace(m, dark=replace(m.dark, minions=(minion,), shots=()))
    m = replace(m, player=replace(m.player, facing=Point(0, -1)))
    m, _ = update(m, Punch())
    m, _ = run(m, 1)
    assert m.dark.minions == ()


def test_boss_part_type_is_rect():
    part = BossPart("head", 10, 10, 4, 4, 5, 5)
    assert part.contains(Point(13, 13)) and not part.contains(Point(14, 10))
