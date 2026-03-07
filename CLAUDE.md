# Pocket — Pyxel Game Dev with Elm Architecture

## Architecture

All games follow the **Elm Architecture** (Model-Update-View) adapted for Python/Pyxel.

The main game is `pocket_world.py`.

### Core Components

**Model** — A frozen dataclass holding the entire game state. Models are immutable; `update` returns a new one.

```python
@dataclass(frozen=True)
class Model:
    player: Player
    enemies: tuple[Enemy, ...]
    score: int
    state: GameState  # "title" | "play" | "dead" | "win"
```

- Use `tuple` not `list` for collections (frozen dataclasses require hashable fields).
- Use `namedtuple` or frozen dataclasses for sub-structures (e.g. `Point`).
- No mutable state anywhere in the model.

**Messages (Msg)** — Frozen dataclasses representing events that can change the model.

```python
@dataclass(frozen=True)
class Msg:
    pass

@dataclass(frozen=True)
class Tick(Msg):
    pass

@dataclass(frozen=True)
class ChangeDir(Msg):
    direction: Point
```

- One class per event type, inheriting from `Msg`.
- Carry only the data needed for the update.

**Commands (Cmd)** — Frozen dataclasses representing side effects (sound, randomness, quit).

```python
@dataclass(frozen=True)
class Cmd:
    pass

@dataclass(frozen=True)
class PlaySound(Cmd):
    channel: int
    sound_id: int

@dataclass(frozen=True)
class GenerateApple(Cmd):
    snake: tuple[Point, ...]
```

- Commands are **not** executed inside `update` — they are returned alongside the new model.
- Commands may produce new messages (e.g. `GenerateApple` → `AppleGenerated`).

### Pure Functions

**`init() -> tuple[Model, list[Cmd]]`** — Returns the initial model and startup commands.

**`update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]`** — Pure function. Takes current model + message, returns new model + commands. Use `match`/`case` to dispatch on message type.

```python
def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case Tick():
            ...
        case ChangeDir(direction=d):
            ...
    return model, []
```

**`view(model: Model)`** — Reads model, calls pyxel draw functions. No state mutation.

### Impure Shell

**`interpret_cmd(cmd: Cmd) -> list[Msg]`** — Executes side effects (pyxel.play, pyxel.rndi, pyxel.quit) and returns any resulting messages.

**`App` class** — The thin shell that wires everything together:

```python
class App:
    def __init__(self):
        pyxel.init(WIDTH, HEIGHT, title="Game", fps=30)
        self.model, cmds = init()
        self._process_cmds(cmds)
        pyxel.run(self._update, self._draw)

    def _collect_input(self) -> list[Msg]:
        msgs = []
        # Map pyxel.btn/btnp calls to Msg objects
        if pyxel.btnp(pyxel.KEY_UP):
            msgs.append(ChangeDir(direction=UP))
        msgs.append(Tick())
        return msgs

    def _update(self):
        for msg in self._collect_input():
            self.model, cmds = update(self.model, msg)
            self._process_cmds(cmds)

    def _process_cmds(self, cmds: list[Cmd]):
        for cmd in cmds:
            new_msgs = interpret_cmd(cmd)
            for msg in new_msgs:
                self.model, new_cmds = update(self.model, msg)
                self._process_cmds(new_cmds)

    def _draw(self):
        view(self.model)
```

### Rules

1. **`update` must be pure** — no pyxel calls, no randomness, no I/O. Return `Cmd` objects instead.
2. **Model is always immutable** — create new dataclass instances, never mutate fields.
3. **Side effects live in `interpret_cmd`** — this is the only place that calls pyxel.play, pyxel.rndi, etc.
4. **Input collection lives in `_collect_input`** — maps pyxel button state to `Msg` objects.
5. **`view` is read-only** — reads model, draws pixels, never modifies state.
6. **One file per game** — keep games self-contained unless complexity demands otherwise.

### File Structure

```txt
pocket/
  CLAUDE.md              # This file
  pyxel_examples/        # Reference examples (07_snake.py is the Elm arch reference)
  water_game.py          # Existing game (OOP style, pre-refactor)
  <new_game>.py          # New games go in project root
```

## Pyxel Conventions

- Screen size: 512x512.
- FPS: 60
- Colors: Pyxel has a fixed 16-color palette (0-15).
- Sounds: Define in a `define_sounds()` function, use `pyxel.sounds[n].set(...)`.
- Input: `pyxel.btn()` for held keys, `pyxel.btnp()` for press events.
- Run: `pyxel run pocket_world.py` — no build step.
