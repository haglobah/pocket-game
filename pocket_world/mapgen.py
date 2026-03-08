import numpy as np

from .constants import (
    MAP_W,
    MAP_H,
    Point,
    SAND,
    SAND_DARK,
    CLIFF,
    CLIFF_EDGE,
    PALM_TREE,
    CACTUS,
    DEAD_BUSH,
    ROCK,
    WATER,
    WATER_DEEP,
    BUSH_GREEN,
    BUSH_FLOWERING,
    BUSH_BERRY,
)
from .model import PlantObject


def _hash_grid(seed: int, cols: int, rows: int) -> np.ndarray:
    """Vectorized deterministic hash for a grid of positions -> [0,1) floats."""
    ix = np.arange(cols, dtype=np.uint32)
    iy = np.arange(rows, dtype=np.uint32)
    # shape (rows, cols) via broadcasting
    h = (
        np.uint32(seed)
        ^ (ix[None, :] * np.uint32(374761393))
        ^ (iy[:, None] * np.uint32(668265263))
    )
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
    h = (
        np.uint32(seed)
        ^ (xs[None, :] * np.uint32(374761393))
        ^ (ys[:, None] * np.uint32(668265263))
    )
    h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
    h = (h ^ (h >> np.uint32(16))) * np.uint32(2024893681)
    h = h ^ (h >> np.uint32(13))
    return (h % np.uint32(1000)).astype(np.float32) * np.float32(0.001)


def generate_map(seed: int) -> tuple[tuple[tuple[int, ...], ...], tuple[PlantObject, ...]]:
    """Generate the 2000x1000 desert tile map and plant objects from a seed."""
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

    # Elevation-based: cliff and cliff edge (raised threshold = less mountains)
    tiles = np.where(elev > 0.70, CLIFF, tiles)
    cliff_edge_mask = (elev > 0.66) & (elev <= 0.70)
    tiles = np.where(cliff_edge_mask, CLIFF_EDGE, tiles)

    # For non-cliff tiles, apply detail/scatter classification
    flat = elev <= 0.66
    # Much sparser plants outside oases
    tiles = np.where(flat & (detail > 0.75) & (scatter > 0.97), PALM_TREE, tiles)
    tiles = np.where(
        flat & (detail < 0.25) & (scatter > 0.98) & (tiles == SAND), CACTUS, tiles
    )
    tiles = np.where(flat & (scatter > 0.995) & (tiles == SAND), DEAD_BUSH, tiles)
    tiles = np.where(flat & (scatter > 0.99) & (tiles == SAND), ROCK, tiles)
    tiles = np.where(flat & (detail > 0.55) & (tiles == SAND), SAND_DARK, tiles)

    # --- Oasis generation 75–100 tiles from spawn (center) ---
    _place_oases(tiles, elev, scatter, seed)

    # Clear all plants within 75 tiles of center (desert before oases)
    cx, cy = MAP_W // 2, MAP_H // 2
    xs = np.arange(MAP_W, dtype=np.float32)
    ys = np.arange(MAP_H, dtype=np.float32)
    dist_from_center = np.sqrt((xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2)
    plant_tiles = (
        (tiles == PALM_TREE)
        | (tiles == CACTUS)
        | (tiles == DEAD_BUSH)
        | (tiles == ROCK)
    )
    tiles = np.where((dist_from_center < 75) & plant_tiles, SAND, tiles)

    # Extract plant objects from tiles and replace with sand
    _PLANT_KIND = {PALM_TREE: "palm_tree", CACTUS: "cactus", BUSH_BERRY: "bush_berry"}
    objects: list[PlantObject] = []
    for tile_type, kind in _PLANT_KIND.items():
        ys_found, xs_found = np.where(tiles == tile_type)
        for y, x in zip(ys_found, xs_found):
            objects.append(PlantObject(anchor=Point(int(x), int(y)), kind=kind, has_fruit=True))
        # Replace plant tiles with sand (use SAND_DARK for variety based on scatter)
        mask = tiles == tile_type
        tiles = np.where(mask & (scatter > 0.5), SAND_DARK, np.where(mask, SAND, tiles))

    # Convert to tuple[tuple[int, ...], ...]
    tilemap = tuple(tuple(int(v) for v in row) for row in tiles)
    return tilemap, tuple(objects)


def _place_oases(
    tiles: np.ndarray,
    elev: np.ndarray,
    scatter: np.ndarray,
    seed: int,
) -> None:
    """Place 3 similarly-sized oases with centers 85–110 tiles from spawn."""
    cx, cy = MAP_W // 2, MAP_H // 2

    # Distance from center for every tile
    xs = np.arange(MAP_W, dtype=np.float32)
    ys = np.arange(MAP_H, dtype=np.float32)
    dist = np.sqrt((xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2)

    # Ring mask: centers at 85–110 so edges start at ~75–100
    ring = (dist >= 85) & (dist <= 110)
    flat = (tiles == SAND) | (tiles == SAND_DARK)
    candidates = ring & flat

    if not candidates.any():
        return

    # Find low-elevation spots in the ring
    masked_elev = np.where(candidates, elev, 1.0)
    threshold = np.percentile(masked_elev[candidates], 20)
    low_spots = candidates & (elev <= threshold)
    low_ys, low_xs = np.where(low_spots)
    if len(low_ys) == 0:
        return

    rng = np.random.RandomState(seed + 9999)
    num_oases = 3

    # Pick 3 oasis centers spread apart (minimum 50 tiles between centers)
    centers = []
    indices = rng.permutation(len(low_ys))
    for idx in indices:
        oy, ox = int(low_ys[idx]), int(low_xs[idx])
        too_close = False
        for py, px in centers:
            if abs(oy - py) + abs(ox - px) < 50:
                too_close = True
                break
        if not too_close:
            centers.append((oy, ox))
            if len(centers) >= num_oases:
                break

    # Paint each oasis with similar size (radius 12–14)
    for oy, ox in centers:
        oasis_radius = rng.randint(12, 15)
        water_radius = oasis_radius - 4
        deep_radius = water_radius - 2

        for dy in range(-oasis_radius, oasis_radius + 1):
            for dx in range(-oasis_radius, oasis_radius + 1):
                ty, tx = oy + dy, ox + dx
                if ty < 0 or ty >= MAP_H or tx < 0 or tx >= MAP_W:
                    continue
                d = (dy * dy + dx * dx) ** 0.5
                current = tiles[ty, tx]

                if current in (CLIFF, CLIFF_EDGE):
                    continue

                if d <= deep_radius:
                    tiles[ty, tx] = WATER_DEEP
                elif d <= water_radius:
                    tiles[ty, tx] = WATER
                elif d <= water_radius + 2:
                    h = (seed ^ (tx * 374761393) ^ (ty * 668265263)) % 1000
                    if h < 333:
                        tiles[ty, tx] = BUSH_GREEN
                    elif h < 666:
                        tiles[ty, tx] = BUSH_FLOWERING
                    else:
                        tiles[ty, tx] = BUSH_BERRY
                elif d <= oasis_radius:
                    h = (seed ^ (tx * 374761393) ^ (ty * 668265263)) % 100
                    if h < 15:
                        tiles[ty, tx] = PALM_TREE
                    elif h < 25:
                        bush_h = h % 3
                        tiles[ty, tx] = [BUSH_GREEN, BUSH_FLOWERING, BUSH_BERRY][bush_h]
