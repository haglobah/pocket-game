# Pocket World — Content Spec

Extracted from the code on 2026-10-17. "Built" means the code implements it.
"Planned" means it is only in `TODO.md` / `WORLDDOC.md`.

## Premise

- A "fancy smart job" person crash-lands on a mysterious pocket world and loses their memory.
- A surviving "time checkpoint machine" in the spaceship wreck respawns them after each death. Each life is a **cycle**.
- Tone: minimal, show-don't-tell. Hostile natural sci-fi world. Caveman-in-a-sci-fi-world vibe.
- Memories return as thought bubbles ("Gedankenblasen").
- Planned story arc: (1) underwater, learn to breathe; (2) above water, learn to breathe again; (3) fix the ship and escape the dying world.

## Game States (built)

`title` → `play` → `dead` → `rewind` → `play` (next cycle).
`play` → portal → `dark_play` → `ending_b` → back to `title`.
`dark_play` → death → `dead`.

### Title screen

- "POCKET WORLD"
- "Enter seed (or press ENTER for random):" — up to 16 chars, `0-9a-z`.
- Seed text is MD5-hashed to an int. Empty input means a random seed.
- Music: title theme.

### Death screen

- "Cycle N -- You died"
- "Seed: …"
- "Reason: …"
- "In this cycle, you learned:" plus a list, or "You didn't learn anything this cycle."
- "[ENTER] Continue" after 60 frames.
- Music: death screen track.

### Rewind screen

- Animated hourglass, 180 frames (3 s).
- "Rewinding..." / "Cycle N+1"
- Then the map regenerates from the same seed. Cycle number +1. Learned skills reset to empty.

### Ending B screen

- "YOU SAVED THE / POCKET WORLD"
- "The dark pocket world has been defeated."
- "The stolen land returns to its rightful place."
- "Peace is restored."
- "-- ENDING B --"
- "[ENTER] Return to Title" — resets the whole game state.

## Controls (built)

| Key | State | Action |
|---|---|---|
| WASD / Arrows | play, dark_play | Move (diagonals allowed) |
| C (hold) | play | Sprint |
| Space | play | Breathe (gills, underwater) |
| B | play | Toggle lungs / gills |
| Q | play | Drink |
| E | play | Eat |
| M | play | Toggle minimap |
| 1 / 2 | play | Pick wizard dialogue option |
| F | dark_play | Punch |
| Enter | title, dead, ending_b | Confirm |

## World (built)

- Map: 2000 × 1000 tiles, 32 px tiles, 24 × 24 tile viewport. Movement wraps at map edges.
- One biome: desert. Seeded value noise (4 elevation octaves + detail + scatter).
- Spawn: nearest walkable tile to map center.

### Tiles

| Tile | Walkable | Notes |
|---|---|---|
| Sand, Dark sand | yes | Base terrain |
| Cliff, Cliff edge | no | Elevation > 0.66 / > 0.70 |
| Palm tree, Cactus | no | Turned into plant objects (food sources) |
| Dead bush | yes | Rare scatter |
| Rock | no | Rare scatter |
| Water, Deep water | swim | Oases only |
| Green / Red / Yellow bush | yes | Oasis markers |
| Portal | yes | Entry to the Dark Pocket World |
| Dark floor / Dark wall | floor only | Dark world tiles (defined) |

### Layout rules

- No plants, rocks or bushes within 75 tiles of spawn. The start is open desert.
- 3 oases in a ring 85–110 tiles from spawn, at low elevation, at least 50 tiles apart.
  - 1 drinkable oasis: green bushes.
  - 2 poisonous oases: red bushes, yellow bushes.
- Portal: placed 3–19 tiles east of spawn. The code comments say "for testing".

## Player Systems (built)

### Movement

- Land: 8 frames per step. Sprint: 4. Water: 12.
- Plant objects block movement.
- Sounds: steps on land, bubbles in water.

### Breathing / O2

- O2 max: 1200 frames (20 s at 60 fps).
- Lungs on land: refills 4 per frame.
- Lungs underwater: loses 180 every second (drowning).
- Gills (anywhere): drains 1 per frame. Space underwater refills 600.
- O2 at 0 means death.

### Hydration

- Max 5 min, start 1 min, drains 1 per frame.
- Q next to or in water: +1 min.
- Poisonous oasis water: +1 min, then poison for 10 s, which drains 6 O2 per frame. Usually fatal.

### Hunger

- Max 10 min, start 3 min, drains 1 per frame.
- E next to a palm tree or cactus with fruit: +5 min. That plant is then empty for the rest of the cycle.
- Note: both plant kinds are safe right now. No danger is modeled yet.

### Death reasons

- "Suffocated from poisoned water"
- "Drowned (lungs underwater)"
- "Suffocated (gills ran dry)"
- "Ran out of oxygen"
- "Died of dehydration"
- "Died of starvation"
- "The wizard's blue bolts drained your oxygen"
- "Defeated in the Dark Pocket World"

### Learned skills (shown on death screen)

walking on land, sprinting, swimming, breathing underwater, switching to lungs, switching to gills, drinking water, eating plants.

## Thought Bubbles / Memories (built)

Typing effect at 3 frames per char. Held 3 s. 10 s cooldown. First one 3 s after spawn. Each is shown once per game. The first unseen eligible memory wins.

| ID | Condition | Text |
|---|---|---|
| awakening | — | "Where... am I?" |
| water_sense | learned breathing underwater | "The water feels familiar. Like I've breathed it before." |
| land_legs | learned walking on land | "Solid ground... my legs remember this." |
| breath_switch | learned switching to lungs | "I can change how I breathe... what am I?" |
| machine | cycle ≥ 2 | "That machine... it pulled me back somehow." |
| not_belong | cycle ≥ 2 | "These people... they're nothing like me. I don't belong here." |
| crash | cycle ≥ 3 | "I remember a ship... falling... a crash." |
| world_wrong | cycle ≥ 4 | "Something is wrong with this place. The edges feel... thin." |
| mission | cycle ≥ 5 | "I was supposed to save them. That was my purpose." |
| wormhole | cycle ≥ 6 | "There's a darkness at the edge. Pulling at everything." |

## Wise Man / Wizard NPC (built)

- Spawns 10–18 tiles from the player.
- Idle lines, every 6 s, starting after 5 s:
  - "The desert speaks in riddles..."
  - "I've seen many like you wander these sands."
  - "Water hides more secrets than you think."
  - "The portal stirs. Can you feel it?"
  - "Every cycle teaches something new."
  - "Careful where you drink, traveller."
- Within 3 tiles, a dialogue tree starts (keys 1/2):
  - **opening:** "I have waited long for a visitor. Tell me — do you wish to survive this desert, or do you blame it for your suffering?"
    1. "I want to survive." → survive_1
    2. "This desert is a curse." → blame_1
  - **survive_1:** "Survival demands trust. Will you walk with me, or walk alone?"
    1. "Walk with me." → follow
    2. "I walk alone." → attack
  - **blame_1:** "Blame breeds enemies. Do you still seek a companion, or will you face me?"
    1. "I seek a companion." → follow
    2. "I will face you." → attack
- **Follow:** "Wise choice. Stay close, and I will walk with you." He follows the player every 12 frames. In the dark world he becomes a companion. He shoots the nearest enemy within 18 tiles: 1 damage every 20 frames.
- **Attack:** "Then defend yourself. My staff speaks in blue lightning." Blue bolts every 24 frames. Each hit costs 300 O2.

## Dark Pocket World (built)

- Entered by stepping on the portal. It reuses the overworld map with dark sprites. Boss theme music.
- Player: 5 HP. 60 i-frames after a hit. Punch range 2 tiles in the facing direction. Punch cooldown 20 frames.
- **Boss:** 20 tiles north of map center. Parts:
  - head: 5 HP, 4 × 4
  - wings: 3 HP, 10 × 4
  - left arm: 3 HP, 3 × 4
  - right arm: 3 HP, 3 × 4
- The head fires an aimed projectile every 96 frames. Projectiles move every 5 frames.
- **Minions:** spawn within ±40 tiles of the boss. They chase the player and deal contact damage.

| Kind | HP | Move delay (frames) | Count |
|---|---|---|---|
| squid | 2 | 45 | 2 |
| squid_small | 1 | 35 | 3 |
| scorpion | 3 | 55 | 2 |
| golem | 4 | 70 | 2 |

- Damage: projectiles, minion contact. Each costs 1 HP.
- Win: destroy all boss parts → Ending B. Lose: HP 0 → death screen.
- HUD: "Boss: n/m parts", "HP:x/5 [F] Punch [WASD/Arrows] Move", minion count.

## HUD / UI (built)

- Bars: "O2 [LUNGS|GILLS]" (shown only when relevant), "Water [Q]", "Food [E]".
- Minimap with "[M] Map".
- Debug strip at the bottom (60 px).
- Font: Pixel Operator SC.

## Audio

| Key | File | Used |
|---|---|---|
| main_theme | 00_soundtrack_main.wav | play |
| boss_theme | 01_soundtrack_boss_fight.wav | dark world |
| title_theme | 02_titlescreen_new.wav | title |
| death_theme | 03_death_screen_track.wav | death screen |
| step / swim | 16_steps.ogg / 17_water_bubble.ogg | movement |
| drowning / suffocating / dehydration / starvation | 23–26 | deaths |
| killed_by_enemy | 27_killed_by_enemy.ogg | enemy death |
| bite | 31_bite.ogg | eating |
| punch | 41_punch.ogg | punch |
| thought | 47_thought_bubble.ogg | thoughts, wizard lines |

## Art Assets

- `sprites/`: environment_sprites, karl_sprites (player, "Karl"), hourglass_frames, wise-man front/left/right, also_without_berries (empty plants).
- `dark_pocket_world/`: boss (head, wings, arms), minions, portal, dark_environment_sprites.
- `art/`: spaceship.png, spaceship-small.png. These are not used in the code yet.
- Style: simple mono color. The player character looks out of place: more fancy and tech than the locals.

## Planned (not built)

- **Biomes:** underwater region, transition zones, spaceship wreck start, NPC settlements, books with hints, fixed trial structures.
- **Jump** (progressive height) and **sprint unlock** via a boots trial. Sprint is currently always available on C.
- **Death timer / world-death countdown.**
- **Eight trials**, each with a deadly choice and skill-based clues:
  1. Drink — 3 water colors, plants show which is safe. *Partly built: the oases.*
  2. Food — coconut (falls on head), cactus (stings), eucalyptus (poisons). Terrain density signals danger.
  3. Read — 1 of 3 NPCs gives a book. The other 2 kill you.
  4. Jump — timing. Jump too high and the fall kills you.
  5. Sprint — 3 boots. 2 of them burn on hot ground. Pick by craftsmanship.
  6. Punch — bar-fight QTE. 8 guys you can punch, 1 you must not fight.
  7. Electric shock — 3 metal hats, lightning strike. The book holds the water+plant clue for the right hat.
  8. Lock breaking (runes) — number sequence puzzle, wrong answer is a trap.
- **Ending A (bad):** get the space-carpet NPC's carpet working (needs shock), escape, watch the world get sucked into the wormhole, learn you were sent to save it.
- **Ending B (good):** gather abilities fast, enter the wormhole, boss fight. The time you get depends on your speed. Abilities are optional but help. The dark world was stealing land because its own world is small and sad.
- **NPC lines:**
  - "I saw some people coming from the west, it seemed like they were fleeing from something"
  - "It's getting a little cramped around here"
- **Effects:** wormhole visual, lightning, dehydration/starvation screen effects, region transitions.
- **Sounds:** underwater theme, sand/grass steps, jump, sprint, shock, drink, pickup, throw, water in/out, respawn.
- **QoL:** save game, minimap shows only explored area.

## Inconsistencies Found

- `CLAUDE.md` says Pyxel, 512 × 512, 30/60 fps. The app uses **arcade**, and the screen is 768 × 828 (24 × 32 + 60).
- Constant comments are wrong: O2_MAX says "40 seconds" but is 20 s. HUNGER_START says "10 min" but is 3 min.
- `killed_by_enemy` loads `27_killed_by_enemy.ogg`, but the file is `27_killedbyhostile.ogg`. That sound is silent.
- `hit`, `boss_fire` and `victory` are played but never loaded. They are silent.
- `sounds_overview.md` gives 25 to both Dehydration and Starvation. Steps 16–19 list jump/land, which don't exist.
- `TODO.md` lists diagonal movement as both done and open.
- `EnterDarkWorld`, `BossPartDestroyed`, `PlayerHit` and `Die` messages exist but nothing emits them.
- `DARK_ARENA_W/H` and the dark floor/wall tiles are defined, but the dark world reuses the overworld map.
- Leftover `app.py.bak` and `view.py.bak` in the package.
