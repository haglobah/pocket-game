
# Story & World Overview

- Style: minimal "show don't tell", mysterious hostile natural world scifi, caveman-in-scifi-world vibe
- Memory snippets return over time as "Gedankenblasen" (thought bubbles)
- Main character: "fancy smart job" person sent to save mysterious pocket world
- Crash-landed, lost all memory, spaceship wreck has a surviving "time checkpoint machine" (respawn point)
- Quests teach abilities; two endings depending on player choices

# Map Generation

- [ ] One big procedurally generated connected map with distinct biome regions
- [ ] Desert region (start area — spaceship wreck / spawn point)
- [ ] Underwater region
- [ ] Transition zones between biomes
- [ ] Specific structures placed in the world for trials/events (not fully random)
- [ ] Dark Pocket World — separate boss fight map (entered via dark wormhole)
- [ ] NPC settlements / points of interest placed in map
- [ ] Books/hints scattered across the world (number sequences, social cues, craftsmanship hints)

# Core Mechanics

## Movement
- [ ] Walk in all 4 directions
- [ ] Diagonal movement (hold two directions at once)
- [ ] Jump mechanic (progressive — learn to jump higher over time)
- [ ] Sprint mechanic (unlocked via boots trial)

## Survival
- [ ] Dehydration system — must drink water or die
- [ ] Starvation system — must eat food or die
- [ ] Death → respawn at spaceship wreck (time checkpoint machine)
- [ ] Timer / cycle tracking (Cycle 1, Cycle 2, ...)

## Underwater Region (ideas — low priority)
- [ ] Walking/swimming in water
- [ ] Gill/lung mode toggle?
- [ ] O2 bar that depletes?
- [ ] Breathe keypress while in water?

# Abilities / Trials of Progression

Each ability is learned through a trial with deadly choices and skill-based clues.

## 1. Drink Water
- [ ] 3 water colors — only 1 is drinkable, other 2 kill you
- [ ] Plants around water indicate if it is safe
- [ ] Needed: survive dehydration (both endings)

## 2. Collect Food
- [ ] 3 different plants: coconut, cactus, eucalyptus
- [ ] Each has a deadly failure mode (coconut falls on head, cactus stings, eucalyptus poisons)
- [ ] Procedural terrain determines danger (cactus density = cactus kills)
- [ ] Needed: survive starvation (both endings)

## 3. Read
- [ ] 1 out of 3 NPCs gives you a book — the other 2 kill you
- [ ] Social cues written somewhere hint at the right NPC
- [ ] Needed: read hints/messages across the world (Ending A), read end credits (Ending B)

## 4. Jump
- [ ] Timing-based trial — jump progressively higher
- [ ] Death: jumped too high and fell
- [ ] Needed: reach higher elevations (Ending A), dodge circular growing damage rings (Ending B)

## 5. Sprint
- [ ] 3 boots you can buy — 2 of 3 burn on hot surface
- [ ] Detect craftsmanship to pick the right pair
- [ ] Needed: sprint over hot ground between safe spots (Ending A), dodge projectiles (Ending B)

## 6. Basic Weapon (Punch)
- [ ] Bar fight QTE — 8 guys to punch, 1 you should not fight
- [ ] Social cues / communication hint at who to avoid
- [ ] Needed: punch through walls (Ending A), punch enemies (Ending B)

## 7. Special Weapon (Electric Shock)
- [ ] 3 metal hats — get struck by lightning — 2 kill you
- [ ] Correct hat determined by combination of water/plant info, written in a book
- [ ] Needed: start magic escape carpet (Ending A), electrocute punch-resistant enemies (Ending B)

## 8. Lock Breaking (Rune Casting)
- [ ] Number sequence puzzle — wrong answer = fall into trap
- [ ] Number sequences hidden across world in books and other places
- [ ] Needed: break into library or similar (Ending A), open locked chests for boosts/heals (Ending B)

# Endings

## Ending A — Escape (Bad Ending)
- [ ] Find the NPC with the space carpet
- [ ] Complete quests to get carpet working (requires Electric Shock ability)
- [ ] Escape the world
- [ ] See the world being destroyed / sucked into dark wormhole on the way out
- [ ] Learn you were originally sent to save it

## Ending B — Save the World (Good Ending)
- [ ] Recollect all abilities as fast as possible
- [ ] Enter the dark wormhole → Dark Pocket World
- [ ] Time for boss fight depends on how fast you got there
- [ ] Can enter without all abilities (but they help in the fight)
- [ ] Defeat boss and minions → stolen land returns to good pocket world
- [ ] The dark pocket world was stealing land because theirs is small and sad

# NPCs & Dialog

- [ ] Space carpet guy (Ending A path)
- [ ] 3 book NPCs (1 helpful, 2 deadly) for Read trial
- [ ] Bar fight NPCs (8 fighters + 1 dangerous) for Punch trial
- [ ] Boot seller NPCs for Sprint trial
- [ ] Hat seller / lightning trial NPCs
- [ ] Settlers with dialog hinting at the dark wormhole threat
- [ ] Dialog: "I saw some people coming from the west, it seemed like they were fleeing from something"
- [ ] Dialog: "It's getting a little cramped around here"
- [ ] Gedankenblasen — memory fragment system (learn: where he is, world going under, his capabilities, respawn machine purpose, original mission)

# Screens

- [ ] Start screen
- [ ] Death screen:
    - Seed displayed
    - Cycle N — You died
    - Reason of death
    - Hourglass going backwards
    - "In this cycle, you... → learnt to [ability]"
- [ ] Ending A screen
- [ ] Ending B screen / credits (requires Read ability to read them)

# Visual Effects

- [ ] Gedankenblasen (thought bubble) display for memory snippets
- [ ] Dark wormhole visual (world being sucked in)
- [ ] Lightning strike effect (hat trial)
- [ ] Dehydration / starvation screen effects
- [ ] Region transition effects

# Sounds

## Track
- [ ] Overworld theme
- [ ] Underwater theme
- [ ] Dark Pocket World / boss theme
- [ ] Death jingle

## Effects
- [ ] Walk on sand
- [ ] Walk on grass
- [ ] Jump
- [ ] Sprint
- [ ] Punch
- [ ] Electric shock
- [ ] Drink water
- [ ] Eat food
- [ ] Interact / pick up item
- [ ] Throw something
- [ ] Into water / out of water
- [ ] Death sound
- [ ] Respawn at checkpoint
- [ ] Gedankenblase appearing

# Quality of Life

- [ ] Diagonal movement (hold two directions at once)
- [ ] Save game?

# Art Style

- Simple mono color (per the design doc)
- Main character looks out of place — more fancy/tech than the rural pocket world inhabitants
