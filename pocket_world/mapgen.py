import hashlib

from .constants import (
    MAP_W,
    MAP_H,
    WATER,
    SAND,
    TREE,
    BUSH,
    TALL_GRASS,
    GRASS,
    FLOWERS,
    ROCK,
    DIRT,
)


def _hash_pos(seed: int, x: int, y: int) -> int:
    """Deterministic hash for a tile position given a seed."""
    data = f"{seed}:{x}:{y}".encode()
    return int(hashlib.md5(data).hexdigest(), 16)


def _noise(seed: int, x: int, y: int, scale: float) -> float:
    """Simple value noise with bilinear interpolation."""
    sx = x / scale
    sy = y / scale
    ix, iy = int(sx), int(sy)
    fx, fy = sx - ix, sy - iy
    # Smooth interpolation
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    # Corner values
    v00 = (_hash_pos(seed, ix, iy) % 1000) / 1000.0
    v10 = (_hash_pos(seed, ix + 1, iy) % 1000) / 1000.0
    v01 = (_hash_pos(seed, ix, iy + 1) % 1000) / 1000.0
    v11 = (_hash_pos(seed, ix + 1, iy + 1) % 1000) / 1000.0
    # Bilinear
    top = v00 * (1 - fx) + v10 * fx
    bot = v01 * (1 - fx) + v11 * fx
    return top * (1 - fy) + bot * fy


def generate_map(seed: int) -> tuple[tuple[int, ...], ...]:
    """Generate the 100x100 tile map from a seed. Returns tuple of rows."""
    rows = []
    for y in range(MAP_H):
        row = []
        for x in range(MAP_W):
            elevation = _noise(seed, x, y, 12.0)
            moisture = _noise(seed + 9999, x, y, 15.0)
            detail = _noise(seed + 5555, x, y, 5.0)

            if elevation < 0.30:
                tile = WATER
            elif elevation < 0.36:
                tile = SAND
            elif elevation < 0.75:
                if moisture > 0.65:
                    if detail > 0.6:
                        tile = TREE
                    elif detail > 0.45:
                        tile = BUSH
                    else:
                        tile = TALL_GRASS
                elif moisture > 0.4:
                    if detail > 0.75:
                        tile = FLOWERS
                    elif detail > 0.55:
                        tile = TALL_GRASS
                    else:
                        tile = GRASS
                else:
                    if detail > 0.7:
                        tile = ROCK
                    else:
                        tile = DIRT
            else:
                if detail > 0.5:
                    tile = ROCK
                else:
                    tile = DIRT
            row.append(tile)
        rows.append(tuple(row))
    return tuple(rows)
