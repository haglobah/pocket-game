import numpy as np

from .constants import (
    MAP_W,
    MAP_H,
    SAND,
    SAND_DARK,
    CLIFF,
    CLIFF_EDGE,
    PALM_TREE,
    CACTUS,
    DEAD_BUSH,
    ROCK,
)


def _hash_grid(seed: int, cols: int, rows: int) -> np.ndarray:
    """Vectorized deterministic hash for a grid of positions -> [0,1) floats."""
    ix = np.arange(cols, dtype=np.uint32)
    iy = np.arange(rows, dtype=np.uint32)
    # shape (rows, cols) via broadcasting
    h = (np.uint32(seed) ^ (ix[None, :] * np.uint32(374761393))
         ^ (iy[:, None] * np.uint32(668265263)))
    h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
    h = (h ^ (h >> np.uint32(16))) * np.uint32(2024893681)
    h = h ^ (h >> np.uint32(13))
    return (h % np.uint32(10000)).astype(np.float32) * np.float32(0.0001)


def _sample_noise(grid: np.ndarray, scale: float) -> np.ndarray:
    """Bilinear interpolation of noise grid at every (x, y) in the map."""
    xs = np.arange(MAP_W, dtype=np.float32) / np.float32(scale)
    ys = np.arange(MAP_H, dtype=np.float32) / np.float32(scale)

    ix = xs.astype(np.int32)
    iy = ys.astype(np.int32)

    fx = xs - ix.astype(np.float32)
    fy = ys - iy.astype(np.float32)

    # Smoothstep
    fx = fx * fx * (np.float32(3.0) - np.float32(2.0) * fx)
    fy = fy * fy * (np.float32(3.0) - np.float32(2.0) * fy)

    # 2D bilinear: grid[iy, ix] etc.  Shape: (MAP_H, MAP_W)
    tl = grid[iy[:, None], ix[None, :]]
    tr = grid[iy[:, None], ix[None, :] + 1]
    bl = grid[iy[:, None] + 1, ix[None, :]]
    br = grid[iy[:, None] + 1, ix[None, :] + 1]

    top = tl + (tr - tl) * fx[None, :]
    bot = bl + (br - bl) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def _scatter_grid(seed: int) -> np.ndarray:
    """Vectorized hash for per-tile scatter values in [0, 1)."""
    xs = np.arange(MAP_W, dtype=np.uint32)
    ys = np.arange(MAP_H, dtype=np.uint32)
    h = (np.uint32(seed) ^ (xs[None, :] * np.uint32(374761393))
         ^ (ys[:, None] * np.uint32(668265263)))
    h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
    h = (h ^ (h >> np.uint32(16))) * np.uint32(2024893681)
    h = h ^ (h >> np.uint32(13))
    return (h % np.uint32(1000)).astype(np.float32) * np.float32(0.001)


def generate_map(seed: int) -> tuple[tuple[int, ...], ...]:
    """Generate the 2000x1000 desert tile map from a seed."""
    # Build noise grids and sample all 4 elevation octaves
    weights = np.array([1.0, 0.5, 0.25, 0.125], dtype=np.float32)
    total_weight = weights.sum()

    scale = 80.0
    elev = np.zeros((MAP_H, MAP_W), dtype=np.float32)
    for i in range(4):
        cols = int(MAP_W / scale) + 3
        rows = int(MAP_H / scale) + 3
        grid = _hash_grid(seed + i * 7777, cols, rows)
        elev += _sample_noise(grid, scale) * weights[i]
        scale *= 0.5

    elev /= total_weight

    # Detail noise
    detail_scale = 20.0
    dcols = int(MAP_W / detail_scale) + 3
    drows = int(MAP_H / detail_scale) + 3
    detail_grid = _hash_grid(seed + 5555, dcols, drows)
    detail = _sample_noise(detail_grid, detail_scale)

    # Scatter
    scatter = _scatter_grid(seed + 3333)

    # Classify tiles (start with SAND=0)
    tiles = np.zeros((MAP_H, MAP_W), dtype=np.int32)

    # Elevation-based: cliff and cliff edge
    tiles = np.where(elev > 0.62, CLIFF, tiles)
    cliff_edge_mask = (elev > 0.58) & (elev <= 0.62)
    tiles = np.where(cliff_edge_mask, CLIFF_EDGE, tiles)

    # For non-cliff tiles, apply detail/scatter classification
    flat = (elev <= 0.58)
    tiles = np.where(flat & (detail > 0.65) & (scatter > 0.92), PALM_TREE, tiles)
    tiles = np.where(flat & (detail < 0.35) & (scatter > 0.95) & (tiles == SAND), CACTUS, tiles)
    tiles = np.where(flat & (scatter > 0.985) & (tiles == SAND), DEAD_BUSH, tiles)
    tiles = np.where(flat & (scatter > 0.975) & (tiles == SAND), ROCK, tiles)
    tiles = np.where(flat & (detail > 0.55) & (tiles == SAND), SAND_DARK, tiles)

    # Convert to tuple[tuple[int, ...], ...]
    return tuple(tuple(int(v) for v in row) for row in tiles)
