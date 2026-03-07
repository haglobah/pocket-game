import pyxel
import math
import random

SCREEN_W = 200
SCREEN_H = 200
TILE = 16
WORLD_W = 800
WORLD_H = 800
COLS = WORLD_W // TILE
ROWS = WORLD_H // TILE
SPEED = 1.5
BREATH_MAX = 300  # 10 seconds at 30 fps

DEEP = 0
SHALLOW = 1
CORAL = 2
ROCK = 3
KELP = 4
SAND = 5


class Bubble:
    __slots__ = ["x", "y", "r", "dy", "life", "phase"]

    def __init__(self, x, y):
        self.x = x + random.uniform(-3, 3)
        self.y = y
        self.r = random.uniform(1, 2.5)
        self.dy = random.uniform(0.4, 0.9)
        self.life = random.randint(20, 50)
        self.phase = random.uniform(0, 6.28)


class Fish:
    __slots__ = ["x", "y", "vx", "vy", "color", "sz", "timer"]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        a = random.uniform(0, 6.28)
        s = random.uniform(0.2, 0.7)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s
        self.color = random.choice([8, 9, 10, 11, 14])
        self.sz = random.choice([2, 3])
        self.timer = random.randint(60, 180)


class Gem:
    __slots__ = ["x", "y", "alive"]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True


class Game:
    def __init__(self):
        pyxel.init(SCREEN_W, SCREEN_H, title="Deep Blue Explorer", fps=30)
        self.setup_sounds()
        self.state = "title"
        self.build_world()
        self.init_play()
        pyxel.run(self.update, self.draw)

    def setup_sounds(self):
        pyxel.sounds[0].set("g2c3e3", "sss", "432", "nnn", 15)
        pyxel.sounds[1].set("a2a2", "pp", "43", "nn", 8)
        pyxel.sounds[2].set("c3e3g3c4", "ssss", "4444", "nnnn", 20)
        pyxel.sounds[3].set("e2c2a1e1", "nnnn", "4321", "ffff", 8)

    # ------------------------------------------------------------------ world
    def build_world(self):
        random.seed(random.randint(0, 99999))
        self.tiles = [[DEEP] * COLS for _ in range(ROWS)]

        for _ in range(25):
            cx, cy = random.randint(4, COLS - 4), random.randint(4, ROWS - 4)
            rad = random.randint(2, 5)
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    if dx * dx + dy * dy <= rad * rad:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < COLS and 0 <= ny < ROWS:
                            self.tiles[ny][nx] = SAND

        snap = [row[:] for row in self.tiles]
        for r in range(ROWS):
            for c in range(COLS):
                if snap[r][c] == SAND:
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < ROWS and 0 <= nc < COLS:
                                if self.tiles[nr][nc] == DEEP and random.random() < 0.7:
                                    self.tiles[nr][nc] = SHALLOW

        for _ in range(35):
            cx, cy = random.randint(2, COLS - 2), random.randint(2, ROWS - 2)
            for _ in range(random.randint(2, 6)):
                if 0 <= cx < COLS and 0 <= cy < ROWS:
                    if self.tiles[cy][cx] in (DEEP, SHALLOW):
                        self.tiles[cy][cx] = CORAL
                cx += random.choice([-1, 0, 1])
                cy += random.choice([-1, 0, 1])

        for _ in range(12):
            cx, cy = random.randint(3, COLS - 3), random.randint(3, ROWS - 3)
            rad = random.randint(1, 2)
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    if dx * dx + dy * dy <= rad * rad:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < COLS and 0 <= ny < ROWS:
                            self.tiles[ny][nx] = ROCK

        for _ in range(80):
            sx, sy = random.randint(0, COLS - 1), random.randint(0, ROWS - 1)
            if self.tiles[sy][sx] in (DEEP, SHALLOW):
                self.tiles[sy][sx] = KELP

        mid_c, mid_r = COLS // 2, ROWS // 2
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                self.tiles[mid_r + dr][mid_c + dc] = SHALLOW

        self.gems = []
        for _ in range(15):
            for _try in range(30):
                tx, ty = random.randint(2, COLS - 2), random.randint(2, ROWS - 2)
                if self.tiles[ty][tx] in (DEEP, SHALLOW, SAND):
                    self.gems.append(Gem(tx * TILE + TILE // 2, ty * TILE + TILE // 2))
                    break

        self.fishes = []
        for _ in range(35):
            for _try in range(10):
                fx = random.uniform(20, WORLD_W - 20)
                fy = random.uniform(20, WORLD_H - 20)
                c, r = int(fx) // TILE, int(fy) // TILE
                if 0 <= c < COLS and 0 <= r < ROWS and self.tiles[r][c] != ROCK:
                    self.fishes.append(Fish(fx, fy))
                    break

    def init_play(self):
        self.px = WORLD_W / 2
        self.py = WORLD_H / 2
        self.pdir = 0
        self.breath = BREATH_MAX
        self.score = 0
        self.collected = 0
        self.total = len(self.gems)
        self.bubbles = []
        self.cx = 0.0
        self.cy = 0.0
        self.t = 0
        self.flash = 0
        self.warned = False

    def tile_at(self, wx, wy):
        c, r = int(wx) // TILE, int(wy) // TILE
        if 0 <= c < COLS and 0 <= r < ROWS:
            return self.tiles[r][c]
        return ROCK

    def solid(self, wx, wy):
        return self.tile_at(wx, wy) == ROCK

    def try_move(self, dx, dy):
        h = 4
        nx, ny = self.px + dx, self.py + dy
        if dx != 0:
            if not (
                self.solid(nx - h, self.py - h)
                or self.solid(nx + h, self.py - h)
                or self.solid(nx - h, self.py + h)
                or self.solid(nx + h, self.py + h)
            ):
                self.px = nx
        if dy != 0:
            if not (
                self.solid(self.px - h, ny - h)
                or self.solid(self.px + h, ny - h)
                or self.solid(self.px - h, ny + h)
                or self.solid(self.px + h, ny + h)
            ):
                self.py = ny
        self.px = max(8, min(WORLD_W - 8, self.px))
        self.py = max(8, min(WORLD_H - 8, self.py))

    # ---------------------------------------------------------------- update
    def update(self):
        self.t += 1
        if self.state == "title":
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.state = "play"
            return
        if self.state in ("dead", "win"):
            if pyxel.btnp(pyxel.KEY_R):
                self.build_world()
                self.init_play()
                self.state = "play"
            return

        dx = dy = 0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -SPEED
            self.pdir = 1
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = SPEED
            self.pdir = 0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -SPEED
            self.pdir = 2
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = SPEED
            self.pdir = 3
        if dx and dy:
            dx *= 0.707
            dy *= 0.707
        self.try_move(dx, dy)

        self.breath -= 1
        if self.flash > 0:
            self.flash -= 1
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.breath = BREATH_MAX
            self.flash = 12
            self.warned = False
            pyxel.play(0, 0)
            for _ in range(6):
                self.bubbles.append(Bubble(self.px, self.py - 6))

        if self.breath < BREATH_MAX * 0.25:
            if not self.warned:
                pyxel.play(1, 1)
                self.warned = True
            elif self.t % 30 == 0:
                pyxel.play(1, 1)
        if self.breath < BREATH_MAX * 0.35 and self.t % 20 == 0:
            self.bubbles.append(Bubble(self.px, self.py - 5))
        if self.breath <= 0:
            self.state = "dead"
            pyxel.play(2, 3)
            return

        for g in self.gems:
            if g.alive:
                ddx, ddy = self.px - g.x, self.py - g.y
                if ddx * ddx + ddy * ddy < 100:
                    g.alive = False
                    self.score += 100
                    self.collected += 1
                    self.breath = min(BREATH_MAX, self.breath + BREATH_MAX // 5)
                    pyxel.play(3, 2)
                    if self.collected >= self.total:
                        self.state = "win"
                        return

        self.cx += (self.px - SCREEN_W / 2 - self.cx) * 0.12
        self.cy += (self.py - SCREEN_H / 2 - self.cy) * 0.12
        self.cx = max(0, min(WORLD_W - SCREEN_W, self.cx))
        self.cy = max(0, min(WORLD_H - SCREEN_H, self.cy))

        for b in self.bubbles:
            b.y -= b.dy
            b.x += math.sin(b.phase + self.t * 0.08) * 0.3
            b.life -= 1
        self.bubbles = [b for b in self.bubbles if b.life > 0]

        for f in self.fishes:
            f.x += f.vx
            f.y += f.vy
            f.timer -= 1
            if f.timer <= 0:
                a = random.uniform(0, 6.28)
                s = random.uniform(0.2, 0.7)
                f.vx = math.cos(a) * s
                f.vy = math.sin(a) * s
                f.timer = random.randint(60, 180)
            fdx, fdy = f.x - self.px, f.y - self.py
            d2 = fdx * fdx + fdy * fdy
            if 0 < d2 < 900:
                d = math.sqrt(d2)
                f.vx = fdx / d * 1.5
                f.vy = fdy / d * 1.5
            if f.x < 10 or f.x > WORLD_W - 10:
                f.vx = -f.vx
                f.x = max(10, min(WORLD_W - 10, f.x))
            if f.y < 10 or f.y > WORLD_H - 10:
                f.vy = -f.vy
                f.y = max(10, min(WORLD_H - 10, f.y))

    # ------------------------------------------------------------------ draw
    def draw(self):
        if self.state == "title":
            self.draw_title()
            return
        pyxel.cls(1)
        ox, oy = int(self.cx), int(self.cy)
        sc, sr = max(0, ox // TILE), max(0, oy // TILE)
        ec = min(COLS, sc + SCREEN_W // TILE + 2)
        er = min(ROWS, sr + SCREEN_H // TILE + 2)
        for r in range(sr, er):
            for c in range(sc, ec):
                self._tile(c * TILE - ox, r * TILE - oy, c, r)

        for g in self.gems:
            if g.alive:
                gx, gy = int(g.x) - ox, int(g.y) - oy
                if -10 < gx < SCREEN_W + 10 and -10 < gy < SCREEN_H + 10:
                    bob = int(math.sin(self.t * 0.1 + g.x * 0.05) * 1.5)
                    gy += bob
                    pyxel.rect(gx - 4, gy - 2, 8, 5, 10)
                    pyxel.rect(gx - 3, gy - 3, 6, 2, 10)
                    pyxel.pset(gx - 2, gy, 9)
                    pyxel.pset(gx + 2, gy, 9)
                    sp = (self.t // 8 + int(g.x)) % 4
                    if sp == 0:
                        pyxel.pset(gx - 5, gy - 4, 10)
                    elif sp == 1:
                        pyxel.pset(gx + 5, gy - 3, 10)

        for f in self.fishes:
            sx, sy = int(f.x) - ox, int(f.y) - oy
            if -10 < sx < SCREEN_W + 10 and -10 < sy < SCREEN_H + 10:
                facing = 1 if f.vx >= 0 else -1
                sz = f.sz
                pyxel.rect(sx - sz, sy - 1, sz * 2, 3, f.color)
                if sz > 2:
                    pyxel.pset(sx - sz, sy - 2, f.color)
                    pyxel.pset(sx + sz - 1, sy - 2, f.color)
                    pyxel.pset(sx - sz, sy + 2, f.color)
                    pyxel.pset(sx + sz - 1, sy + 2, f.color)
                tx = sx - facing * (sz + 1)
                pyxel.pset(tx, sy - 1, f.color)
                pyxel.pset(tx, sy + 1, f.color)
                pyxel.pset(sx + facing * (sz - 1), sy - 1, 7)

        for b in self.bubbles:
            bx, by = int(b.x) - ox, int(b.y) - oy
            if 0 < bx < SCREEN_W and 0 < by < SCREEN_H:
                col = 7 if b.life > 10 else 12
                if b.r > 1.5:
                    pyxel.circb(bx, by, int(b.r), col)
                else:
                    pyxel.pset(bx, by, col)

        self._player(ox, oy)

        ratio = self.breath / BREATH_MAX
        if ratio < 0.3 and self.t % 8 < 4:
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, 8)
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, 8)

        self._hud(ratio)
        if self.state == "dead":
            self._overlay("YOU DROWNED!", 8, f"SCORE: {self.score}", "PRESS R TO RETRY")
        elif self.state == "win":
            self._overlay("ALL GEMS FOUND!", 11, f"SCORE: {self.score}", "PRESS R TO REPLAY")

    def _tile(self, x, y, c, r):
        t = self.tiles[r][c]
        if t == DEEP:
            pyxel.rect(x, y, TILE, TILE, 1)
            if (c + r + self.t // 25) % 7 == 0:
                pyxel.pset(x + (c * 5) % 13, y + (r * 7) % 13, 5)
        elif t == SHALLOW:
            pyxel.rect(x, y, TILE, TILE, 5)
            if (c + r + self.t // 18) % 5 == 0:
                pyxel.pset(x + (c * 3) % 11, y + (r * 5) % 11, 12)
        elif t == CORAL:
            pyxel.rect(x, y, TILE, TILE, 1)
            cc = [8, 14, 2][(c * 7 + r * 3) % 3]
            pyxel.rect(x + 3, y + 4, 4, 8, cc)
            pyxel.rect(x + 9, y + 2, 3, 10, cc)
            pyxel.circ(x + 5, y + 3, 2, cc)
            pyxel.circ(x + 10, y + 1, 1, cc)
        elif t == ROCK:
            pyxel.rect(x, y, TILE, TILE, 13)
            pyxel.rect(x + 2, y + 2, TILE - 4, TILE - 4, 5)
            pyxel.pset(x + 5, y + 5, 6)
        elif t == KELP:
            bg = 5 if (c * 7 + r * 13) % 2 == 0 else 1
            pyxel.rect(x, y, TILE, TILE, bg)
            sway = math.sin(self.t * 0.06 + c) * 2
            pyxel.line(x + 5 + int(sway), y + 1, x + 5, y + 14, 3)
            pyxel.line(x + 11 + int(sway), y + 3, x + 11, y + 14, 11)
            pyxel.pset(x + 5 + int(sway), y + 1, 3)
            pyxel.pset(x + 11 + int(sway), y + 3, 11)
        elif t == SAND:
            pyxel.rect(x, y, TILE, TILE, 15)
            if (c + r) % 3 == 0:
                pyxel.pset(x + 6, y + 6, 10)

    def _player(self, ox, oy):
        px, py = int(self.px) - ox, int(self.py) - oy
        if self.state == "dead" and self.t % 6 > 2:
            return
        moving = (
            pyxel.btn(pyxel.KEY_UP)
            or pyxel.btn(pyxel.KEY_DOWN)
            or pyxel.btn(pyxel.KEY_LEFT)
            or pyxel.btn(pyxel.KEY_RIGHT)
            or pyxel.btn(pyxel.KEY_W)
            or pyxel.btn(pyxel.KEY_A)
            or pyxel.btn(pyxel.KEY_S)
            or pyxel.btn(pyxel.KEY_D)
        )
        pyxel.rect(px - 3, py - 3, 7, 8, 0)
        pyxel.circ(px, py - 5, 3, 15)
        pyxel.rect(px - 2, py - 6, 5, 2, 12)
        pyxel.rect(px - 5, py - 3, 2, 5, 6)
        pyxel.rect(px - 3, py + 5, 3, 2, 3)
        pyxel.rect(px + 1, py + 5, 3, 2, 3)
        arm = int(math.sin(self.t * 0.15) * 2) if moving else 0
        if self.pdir == 0:
            pyxel.line(px - 3, py + 1, px - 5, py + 3 + arm, 15)
            pyxel.line(px + 3, py + 1, px + 5, py + 3 - arm, 15)
        elif self.pdir == 1:
            pyxel.line(px - 3, py - 1, px - 5, py - 5 + arm, 15)
            pyxel.line(px + 3, py - 1, px + 5, py - 5 - arm, 15)
        elif self.pdir == 2:
            pyxel.line(px - 3, py, px - 6, py - 1 + arm, 15)
            pyxel.line(px - 3, py + 2, px - 6, py + 3 - arm, 15)
        else:
            pyxel.line(px + 3, py, px + 6, py - 1 + arm, 15)
            pyxel.line(px + 3, py + 2, px + 6, py + 3 - arm, 15)

    def _hud(self, ratio):
        bw, bh = 56, 6
        bx, by = SCREEN_W - bw - 10, 6
        pyxel.rect(bx - 1, by - 1, bw + 2, bh + 2, 0)
        fill = int(bw * ratio)
        if ratio > 0.5:
            col = 12
        elif ratio > 0.25:
            col = 10
        else:
            col = 8 if self.t % 8 < 4 else 2
        if fill > 0:
            pyxel.rect(bx, by, fill, bh, col)
        pyxel.text(bx - 14, by, "O2", 7)
        if self.flash > 0:
            pyxel.text(bx + bw // 2 - 6, by - 9, "AIR!", 7)
        pyxel.text(4, 4, f"SCORE:{self.score}", 7)
        pyxel.text(4, 13, f"GEMS:{self.collected}/{self.total}", 10)
        if self.t < 150 or (ratio < 0.4 and self.t % 40 < 25):
            c = 7 if self.t % 20 < 14 else 12
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H - 12, "[SPACE] BREATHE", c)
        if self.t < 120:
            pyxel.text(SCREEN_W // 2 - 32, SCREEN_H - 22, "ARROWS/WASD MOVE", 6)
        mm = 40
        mx, my = SCREEN_W - mm - 4, SCREEN_H - mm - 4
        pyxel.rect(mx - 1, my - 1, mm + 2, mm + 2, 0)
        pyxel.rect(mx, my, mm, mm, 1)
        sx, sy = mm / WORLD_W, mm / WORLD_H
        for r in range(0, ROWS, 2):
            for c in range(0, COLS, 2):
                tile = self.tiles[r][c]
                if tile == SAND:
                    pyxel.pset(mx + int(c * TILE * sx), my + int(r * TILE * sy), 15)
                elif tile == ROCK:
                    pyxel.pset(mx + int(c * TILE * sx), my + int(r * TILE * sy), 13)
                elif tile == CORAL:
                    pyxel.pset(mx + int(c * TILE * sx), my + int(r * TILE * sy), 2)
        for g in self.gems:
            if g.alive:
                pyxel.pset(mx + int(g.x * sx), my + int(g.y * sy), 10)
        pmx = mx + int(self.px * sx)
        pmy = my + int(self.py * sy)
        pyxel.rect(pmx - 1, pmy - 1, 3, 3, 8)

    def _overlay(self, title, tcol, line1, line2):
        w, h = 120, 48
        x, y = SCREEN_W // 2 - w // 2, SCREEN_H // 2 - h // 2
        pyxel.rect(x, y, w, h, 0)
        pyxel.rectb(x, y, w, h, tcol)
        pyxel.text(SCREEN_W // 2 - len(title) * 2, y + 8, title, tcol)
        pyxel.text(SCREEN_W // 2 - len(line1) * 2, y + 22, line1, 7)
        pyxel.text(SCREEN_W // 2 - len(line2) * 2, y + 34, line2, 6)

    def draw_title(self):
        pyxel.cls(1)
        for y in range(0, SCREEN_H, 4):
            offset = math.sin(self.t * 0.03 + y * 0.1) * 3
            c = 5 if (y // 4 + self.t // 20) % 3 == 0 else 1
            pyxel.rect(int(offset), y, SCREEN_W, 4, c)
        pyxel.rect(20, 40, 160, 130, 0)
        pyxel.rectb(20, 40, 160, 130, 12)
        pyxel.text(56, 52, "DEEP BLUE", 12)
        pyxel.text(58, 62, "EXPLORER", 7)
        pyxel.text(38, 82, "Explore the ocean and", 6)
        pyxel.text(38, 92, "collect all the gems!", 6)
        pyxel.text(38, 110, "ARROWS/WASD : Move", 7)
        pyxel.text(38, 120, "SPACE       : Breathe", 7)
        pyxel.text(38, 138, "Breathe every 10 sec", 8)
        pyxel.text(38, 148, "or you will drown!", 8)
        if self.t % 40 < 28:
            pyxel.text(44, 176, "PRESS SPACE TO START", 7)
        fx = 30 + (self.t * 2) % (SCREEN_W + 60) - 30
        pyxel.rect(fx, 30, 5, 3, 9)
        pyxel.pset(fx - 2, 29, 9)
        pyxel.pset(fx - 2, 32, 9)
        pyxel.pset(fx + 4, 30, 7)


Game()
