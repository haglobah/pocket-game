# title: Snake!
# author: Marcus Croucher
# desc: A Pyxel snake game example
# site: https://github.com/kitao/pyxel
# license: MIT
# version: 1.0

from dataclasses import dataclass
from collections import namedtuple

import pyxel

Point = namedtuple("Point", ["x", "y"])


#############
# Constants #
#############

COL_BACKGROUND = 3
COL_BODY = 11
COL_HEAD = 7
COL_DEATH = 8
COL_APPLE = 8

TEXT_DEATH = ["GAME OVER", "(Q)UIT", "(R)ESTART"]
COL_TEXT_DEATH = 0
HEIGHT_DEATH = 5

WIDTH = 40
HEIGHT = 50

HEIGHT_SCORE = pyxel.FONT_HEIGHT
COL_SCORE = 6
COL_SCORE_BACKGROUND = 5

UP = Point(0, -1)
DOWN = Point(0, 1)
RIGHT = Point(1, 0)
LEFT = Point(-1, 0)

START = Point(5, 5 + HEIGHT_SCORE)


###########
# Model   #
###########


@dataclass(frozen=True)
class Model:
    direction: Point
    snake: tuple[Point, ...]
    apple: Point
    score: int
    death: bool
    popped_point: Point | None


##############
# Messages   #
##############


@dataclass(frozen=True)
class Msg:
    pass


@dataclass(frozen=True)
class Tick(Msg):
    pass


@dataclass(frozen=True)
class ChangeDir(Msg):
    direction: Point


@dataclass(frozen=True)
class Restart(Msg):
    pass


@dataclass(frozen=True)
class Quit(Msg):
    pass


@dataclass(frozen=True)
class AppleGenerated(Msg):
    position: Point


##############
# Commands   #
##############


@dataclass(frozen=True)
class Cmd:
    pass


@dataclass(frozen=True)
class PlayBgm(Cmd):
    pass


@dataclass(frozen=True)
class PlayEatSound(Cmd):
    pass


@dataclass(frozen=True)
class PlayDeathSound(Cmd):
    pass


@dataclass(frozen=True)
class QuitApp(Cmd):
    pass


@dataclass(frozen=True)
class GenerateApple(Cmd):
    snake: tuple[Point, ...]


################
# Init/Update  #
################

OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


def init() -> tuple[Model, list[Cmd]]:
    model = Model(
        direction=RIGHT,
        snake=(START,),
        apple=START,
        score=0,
        death=False,
        popped_point=None,
    )
    return model, [PlayBgm(), GenerateApple(snake=model.snake)]


def update(model: Model, msg: Msg) -> tuple[Model, list[Cmd]]:
    match msg:
        case ChangeDir(direction=new_dir):
            if model.death:
                return model, []
            if new_dir == OPPOSITE.get(model.direction):
                return model, []
            return Model(
                direction=new_dir,
                snake=model.snake,
                apple=model.apple,
                score=model.score,
                death=model.death,
                popped_point=model.popped_point,
            ), []

        case Tick():
            if model.death:
                return model, []
            old_head = model.snake[0]
            new_head = Point(
                old_head.x + model.direction.x, old_head.y + model.direction.y
            )
            new_snake = (new_head,) + model.snake
            popped = new_snake[-1]
            new_snake = new_snake[:-1]

            # Check death: out of bounds or self-collision
            dead = (
                new_head.x < 0
                or new_head.y < HEIGHT_SCORE
                or new_head.x >= WIDTH
                or new_head.y >= HEIGHT
                or new_head in new_snake[1:]
            )
            if dead:
                return (
                    Model(
                        direction=model.direction,
                        snake=new_snake,
                        apple=model.apple,
                        score=model.score,
                        death=True,
                        popped_point=popped,
                    ),
                    [PlayDeathSound()],
                )

            # Check apple
            if new_head == model.apple:
                grown_snake = new_snake + (popped,)
                return (
                    Model(
                        direction=model.direction,
                        snake=grown_snake,
                        apple=model.apple,
                        score=model.score + 1,
                        death=False,
                        popped_point=None,
                    ),
                    [PlayEatSound(), GenerateApple(snake=grown_snake)],
                )

            return (
                Model(
                    direction=model.direction,
                    snake=new_snake,
                    apple=model.apple,
                    score=model.score,
                    death=False,
                    popped_point=popped,
                ),
                [],
            )

        case AppleGenerated(position=pos):
            return (
                Model(
                    direction=model.direction,
                    snake=model.snake,
                    apple=pos,
                    score=model.score,
                    death=model.death,
                    popped_point=model.popped_point,
                ),
                [],
            )

        case Restart():
            return init()

        case Quit():
            return model, [QuitApp()]

    return model, []


#######################
# Command interpreter #
#######################


def interpret_cmd(cmd: Cmd) -> list[Msg]:
    match cmd:
        case PlayBgm():
            pyxel.playm(0, loop=True)
        case PlayEatSound():
            pyxel.play(0, 0)
        case PlayDeathSound():
            pyxel.stop()
            pyxel.play(0, 1)
        case QuitApp():
            pyxel.quit()
        case GenerateApple(snake=snake):
            snake_pixels = set(snake)
            pos = snake[0]
            while pos in snake_pixels:
                x = pyxel.rndi(0, WIDTH - 1)
                y = pyxel.rndi(HEIGHT_SCORE + 1, HEIGHT - 1)
                pos = Point(x, y)
            return [AppleGenerated(position=pos)]
    return []


########
# View #
########


def center_text(text, page_width, char_width=pyxel.FONT_WIDTH):
    text_width = len(text) * char_width
    return (page_width - text_width) // 2


def view(model: Model):
    if not model.death:
        pyxel.cls(col=COL_BACKGROUND)
        # Draw snake
        for i, point in enumerate(model.snake):
            colour = COL_HEAD if i == 0 else COL_BODY
            pyxel.pset(point.x, point.y, col=colour)
        # Draw score
        score = f"{model.score:04}"
        pyxel.rect(0, 0, WIDTH, HEIGHT_SCORE, COL_SCORE_BACKGROUND)
        pyxel.text(1, 1, score, COL_SCORE)
        # Draw apple
        pyxel.pset(model.apple.x, model.apple.y, col=COL_APPLE)
    else:
        pyxel.cls(col=COL_DEATH)
        display_text = TEXT_DEATH[:]
        display_text.insert(1, f"{model.score:04}")
        for i, text in enumerate(display_text):
            y_offset = (pyxel.FONT_HEIGHT + 2) * i
            text_x = center_text(text, WIDTH)
            pyxel.text(text_x, HEIGHT_DEATH + y_offset, text, COL_TEXT_DEATH)


###############
# App (shell) #
###############


class App:
    def __init__(self):
        pyxel.init(
            WIDTH, HEIGHT, title="Snake!", fps=20, display_scale=12, capture_scale=6
        )
        define_sound_and_music()
        self.model, cmds = init()
        self._process_cmds(cmds)
        pyxel.run(self._update, self._draw)

    def _collect_input(self) -> list[Msg]:
        msgs: list[Msg] = []

        if pyxel.btn(pyxel.KEY_Q):
            msgs.append(Quit())

        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A):
            msgs.append(Restart())

        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_UP):
            msgs.append(ChangeDir(direction=UP))
        elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN):
            msgs.append(ChangeDir(direction=DOWN))
        elif pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT):
            msgs.append(ChangeDir(direction=LEFT))
        elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT):
            msgs.append(ChangeDir(direction=RIGHT))

        msgs.append(Tick())
        return msgs

    def _update(self):
        msgs = self._collect_input()
        for msg in msgs:
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


###########################
# Music and sound effects #
###########################


def define_sound_and_music():
    """Define sound and music."""

    # Sound effects
    pyxel.sounds[0].set(
        notes="c3e3g3c4c4", tones="s", volumes="4", effects=("n" * 4 + "f"), speed=7
    )
    pyxel.sounds[1].set(
        notes="f3 b2 f2 b1  f1 f1 f1 f1",
        tones="p",
        volumes=("4" * 4 + "4321"),
        effects=("n" * 7 + "f"),
        speed=9,
    )

    melody1 = (
        "c3 c3 c3 d3 e3 r e3 r"
        + ("r" * 8)
        + "e3 e3 e3 f3 d3 r c3 r"
        + ("r" * 8)
        + "c3 c3 c3 d3 e3 r e3 r"
        + ("r" * 8)
        + "b2 b2 b2 f3 d3 r c3 r"
        + ("r" * 8)
    )
    melody2 = (
        "rrrr e3e3e3e3 d3d3c3c3 b2b2c3c3"
        + "a2a2a2a2 c3c3c3c3 d3d3d3d3 e3e3e3e3"
        + "rrrr e3e3e3e3 d3d3c3c3 b2b2c3c3"
        + "a2a2a2a2 g2g2g2g2 c3c3c3c3 g2g2a2a2"
        + "rrrr e3e3e3e3 d3d3c3c3 b2b2c3c3"
        + "a2a2a2a2 c3c3c3c3 d3d3d3d3 e3e3e3e3"
        + "f3f3f3a3 a3a3a3a3 g3g3g3b3 b3b3b3b3"
        + "b3b3b3b4 rrrr e3d3c3g3 a2g2e2d2"
    )

    # Music
    pyxel.sounds[2].set(
        notes=melody1 * 2 + melody2 * 2,
        tones="s",
        volumes=("3"),
        effects=("nnnsffff"),
        speed=20,
    )

    harmony1 = (
        "a1 a1 a1 b1  f1 f1 c2 c2  c2 c2 c2 c2  g1 g1 b1 b1" * 3
        + "f1 f1 f1 f1 f1 f1 f1 f1 g1 g1 g1 g1 g1 g1 g1 g1"
    )
    harmony2 = (
        ("f1" * 8 + "g1" * 8 + "a1" * 8 + ("c2" * 7 + "d2")) * 3
        + "f1" * 16
        + "g1" * 16
    )

    pyxel.sounds[3].set(
        notes=harmony1 * 2 + harmony2 * 2,
        tones="t",
        volumes="5",
        effects="f",
        speed=20,
    )
    pyxel.sounds[4].set(
        notes=("f0 r a4 r  f0 f0 a4 r  f0 r a4 r  f0 f0 a4 f0"),
        tones="n",
        volumes="6622 6622 6622 6426",
        effects="f",
        speed=20,
    )

    pyxel.musics[0].set([], [2], [3], [4])


App()
