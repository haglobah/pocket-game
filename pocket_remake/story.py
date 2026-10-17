"""Words: memories, wizard lines, dialogue tree, skills, death reasons."""

# Skills, in the order the death screen lists them
WALK = "walking on land"
SPRINT = "sprinting"
SWIM = "swimming"
BREATHE_WATER = "breathing underwater"
TO_LUNGS = "switching to lungs"
TO_GILLS = "switching to gills"
DRINK = "drinking water"
EAT = "eating plants"

# Death reasons
POISONED = "Suffocated from poisoned water"
DROWNED = "Drowned (lungs underwater)"
GILLS_DRY = "Suffocated (gills ran dry)"
NO_O2 = "Ran out of oxygen"
THIRST = "Died of dehydration"
HUNGER = "Died of starvation"
WIZARD_BOLTS = "The wizard's blue bolts drained your oxygen"
DARK_DEFEAT = "Defeated in the Dark Pocket World"

# (id, condition(learned, cycle), text). The first unseen eligible one wins.
MEMORIES = (
    ("awakening", lambda learned, cycle: True, "Where... am I?"),
    (
        "water_sense",
        lambda learned, cycle: BREATHE_WATER in learned,
        "The water feels familiar. Like I've breathed it before.",
    ),
    (
        "land_legs",
        lambda learned, cycle: WALK in learned,
        "Solid ground... my legs remember this.",
    ),
    (
        "breath_switch",
        lambda learned, cycle: TO_LUNGS in learned,
        "I can change how I breathe... what am I?",
    ),
    (
        "machine",
        lambda learned, cycle: cycle >= 2,
        "That machine... it pulled me back somehow.",
    ),
    (
        "not_belong",
        lambda learned, cycle: cycle >= 2,
        "These people... they're nothing like me. I don't belong here.",
    ),
    (
        "crash",
        lambda learned, cycle: cycle >= 3,
        "I remember a ship... falling... a crash.",
    ),
    (
        "world_wrong",
        lambda learned, cycle: cycle >= 4,
        "Something is wrong with this place. The edges feel... thin.",
    ),
    (
        "mission",
        lambda learned, cycle: cycle >= 5,
        "I was supposed to save them. That was my purpose.",
    ),
    (
        "wormhole",
        lambda learned, cycle: cycle >= 6,
        "There's a darkness at the edge. Pulling at everything.",
    ),
)

WIZARD_IDLE = (
    "The desert speaks in riddles...",
    "I've seen many like you wander these sands.",
    "Water hides more secrets than you think.",
    "The portal stirs. Can you feel it?",
    "Every cycle teaches something new.",
    "Careful where you drink, traveller.",
)

# node -> (text, ((option text, next node), (option text, next node)))
DIALOGUE = {
    "opening": (
        (
            "I have waited long for a visitor. Tell me - do you wish to survive "
            "this desert, or do you blame it for your suffering?"
        ),
        (("I want to survive.", "survive_1"), ("This desert is a curse.", "blame_1")),
    ),
    "survive_1": (
        "Survival demands trust. Will you walk with me, or walk alone?",
        (("Walk with me.", "follow"), ("I walk alone.", "attack")),
    ),
    "blame_1": (
        "Blame breeds enemies. Do you still seek a companion, or will you face me?",
        (("I seek a companion.", "follow"), ("I will face you.", "attack")),
    ),
}

DIALOGUE_END = {
    "follow": "Wise choice. Stay close, and I will walk with you.",
    "attack": "Then defend yourself. My staff speaks in blue lightning.",
}
