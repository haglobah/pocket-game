"""Memory fragment definitions and trigger logic for the Gedankenblasen system.

Memories are ordered by priority — the first matching unseen memory triggers.
Triggers are purely evaluated from model state (cycle count, learned skills).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryFragment:
    id: str
    text: str
    min_cycle: int = 1
    required_skill: str | None = None


MEMORIES: tuple[MemoryFragment, ...] = (
    # Cycle 1 — immediate confusion
    MemoryFragment(
        "awakening",
        "Where... am I?",
    ),
    # Skill-gated — triggered when you first do these things
    MemoryFragment(
        "water_sense",
        "The water feels familiar. Like I've breathed it before.",
        required_skill="breathing underwater",
    ),
    MemoryFragment(
        "land_legs",
        "Solid ground... my legs remember this.",
        required_skill="walking on land",
    ),
    MemoryFragment(
        "breath_switch",
        "I can change how I breathe... what am I?",
        required_skill="switching to lungs",
    ),
    # Cycle 2 — after first death, you start piecing things together
    MemoryFragment(
        "machine",
        "That machine... it pulled me back somehow.",
        min_cycle=2,
    ),
    MemoryFragment(
        "not_belong",
        "These people... they're nothing like me. I don't belong here.",
        min_cycle=2,
    ),
    # Cycle 3 — deeper memories return
    MemoryFragment(
        "crash",
        "I remember a ship... falling... a crash.",
        min_cycle=3,
    ),
    MemoryFragment(
        "world_wrong",
        "Something is wrong with this place. The edges feel... thin.",
        min_cycle=4,
    ),
    MemoryFragment(
        "mission",
        "I was supposed to save them. That was my purpose.",
        min_cycle=5,
    ),
    MemoryFragment(
        "wormhole",
        "There's a darkness at the edge. Pulling at everything.",
        min_cycle=6,
    ),
)

_MEMORIES_BY_ID: dict[str, MemoryFragment] = {m.id: m for m in MEMORIES}


def get_memory(memory_id: str) -> MemoryFragment:
    return _MEMORIES_BY_ID[memory_id]


def check_triggers(
    cycle: int,
    learned: tuple[str, ...],
    seen_memories: tuple[str, ...],
) -> str | None:
    """Return the id of the first unseen memory whose conditions are met, or None."""
    for mem in MEMORIES:
        if mem.id in seen_memories:
            continue
        if cycle < mem.min_cycle:
            continue
        if mem.required_skill is not None and mem.required_skill not in learned:
            continue
        return mem.id
    return None
