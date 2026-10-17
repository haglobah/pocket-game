"""Readable text on a 512 px screen: Pyxel's 4x6 font, doubled.

`build_font` copies the built-in glyphs into a 2x atlas in image bank 2.
Larger sizes are drawn pixel by pixel from the glyph bitmaps.
"""

import pyxel

CHARS = "".join(chr(c) for c in range(32, 127))
GLYPH_W, GLYPH_H = 4, 6
ATLAS_COLS = 32
_glyphs: dict[str, list[tuple[int, int]]] = {}


def build_font() -> None:
    img = pyxel.images[2]
    img.cls(0)
    half = len(CHARS) // 2
    img.text(0, 0, CHARS[:half], 7)
    img.text(0, 8, CHARS[half:], 7)
    for i, ch in enumerate(CHARS):
        ox, oy = ((i % half) * GLYPH_W, 0 if i < half else 8)
        _glyphs[ch] = [
            (x, y)
            for y in range(GLYPH_H)
            for x in range(GLYPH_W)
            if img.pget(ox + x, oy + y) == 7
        ]
    img.cls(0)
    for i, ch in enumerate(CHARS):
        u, v = _atlas(i)
        for x, y in _glyphs[ch]:
            img.rect(u + x * 2, v + y * 2, 2, 2, 7)


def _atlas(i: int) -> tuple[int, int]:
    return (i % ATLAS_COLS) * 8, (i // ATLAS_COLS) * 12


def width(s: str, scale: int = 2) -> int:
    return len(s) * GLYPH_W * scale


def text(x: float, y: float, s: str, col: int, scale: int = 2) -> None:
    x, y = int(x), int(y)
    if scale == 2:
        pyxel.pal(7, col)
        for i, ch in enumerate(s):
            idx = CHARS.find(ch)
            if idx > 0:
                u, v = _atlas(idx)
                pyxel.blt(x + i * 8, y, 2, u, v, 8, 12, 0)
        pyxel.pal()
        return
    for i, ch in enumerate(s):
        for gx, gy in _glyphs.get(ch, ()):
            pyxel.rect(
                x + (i * GLYPH_W + gx) * scale, y + gy * scale, scale, scale, col
            )


def shadow(
    x: float, y: float, s: str, col: int, scale: int = 2, under: int = 0
) -> None:
    text(x + scale // 2 + 1, y + scale // 2 + 1, s, under, scale)
    text(x, y, s, col, scale)


def center(y: float, s: str, col: int, scale: int = 2, under: int | None = 0) -> None:
    x = (pyxel.width - width(s, scale)) / 2
    if under is None:
        text(x, y, s, col, scale)
    else:
        shadow(x, y, s, col, scale, under)


def wrap(s: str, max_chars: int) -> list[str]:
    lines, line = [], ""
    for word in s.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        lines.append(line)
    return lines
