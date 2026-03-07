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


def _hash_pos(seed: int, x: int, y: int) -> int:
    """Fast deterministic hash for a tile position."""
    h = (seed ^ (x * 374761393) ^ (y * 668265263)) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 16)) * 2024893681) & 0xFFFFFFFF
    return (h ^ (h >> 13)) & 0xFFFFFFFF


def _make_grid(seed: int, scale: float) -> list:
    """Precompute noise grid as flat list for fast lookup."""
    cols = int(MAP_W / scale) + 3
    rows_n = int(MAP_H / scale) + 3
    hp = _hash_pos
    grid = [0.0] * (cols * rows_n)
    for iy in range(rows_n):
        off = iy * cols
        for ix in range(cols):
            grid[off + ix] = (hp(seed, ix, iy) % 10000) * 0.0001
    return grid, cols, scale


def generate_map(seed: int) -> tuple[tuple[int, ...], ...]:
    """Generate the 2000x1000 desert tile map from a seed."""
    # Precompute noise grids
    eg = []  # elevation grids (4 octaves)
    s = 80.0
    for i in range(4):
        eg.append(_make_grid(seed + i * 7777, s))
        s *= 0.5
    dg, dc, ds = _make_grid(seed + 5555, 20.0)  # detail grid

    w0, w1, w2, w3 = 1.0, 0.5, 0.25, 0.125
    tw = 1.0 / (w0 + w1 + w2 + w3)

    hp = _hash_pos
    s3 = seed + 3333
    _int = int

    eg0, ec0, es0 = eg[0]
    eg1, ec1, es1 = eg[1]
    eg2, ec2, es2 = eg[2]
    eg3, ec3, es3 = eg[3]

    rows = []
    for y in range(MAP_H):
        row = [0] * MAP_W
        for x in range(MAP_W):
            # Inline FBM: 4 octaves of noise sampling
            # Octave 0
            sx0 = x / es0; sy0 = y / es0
            ix0 = _int(sx0); iy0 = _int(sy0)
            fx0 = sx0 - ix0; fy0 = sy0 - iy0
            fx0 = fx0 * fx0 * (3.0 - 2.0 * fx0)
            fy0 = fy0 * fy0 * (3.0 - 2.0 * fy0)
            o0 = iy0 * ec0 + ix0
            t0 = eg0[o0] + (eg0[o0+1] - eg0[o0]) * fx0
            b0 = eg0[o0+ec0] + (eg0[o0+ec0+1] - eg0[o0+ec0]) * fx0
            n0 = t0 + (b0 - t0) * fy0

            # Octave 1
            sx1 = x / es1; sy1 = y / es1
            ix1 = _int(sx1); iy1 = _int(sy1)
            fx1 = sx1 - ix1; fy1 = sy1 - iy1
            fx1 = fx1 * fx1 * (3.0 - 2.0 * fx1)
            fy1 = fy1 * fy1 * (3.0 - 2.0 * fy1)
            o1 = iy1 * ec1 + ix1
            t1 = eg1[o1] + (eg1[o1+1] - eg1[o1]) * fx1
            b1 = eg1[o1+ec1] + (eg1[o1+ec1+1] - eg1[o1+ec1]) * fx1
            n1 = t1 + (b1 - t1) * fy1

            # Octave 2
            sx2 = x / es2; sy2 = y / es2
            ix2 = _int(sx2); iy2 = _int(sy2)
            fx2 = sx2 - ix2; fy2 = sy2 - iy2
            fx2 = fx2 * fx2 * (3.0 - 2.0 * fx2)
            fy2 = fy2 * fy2 * (3.0 - 2.0 * fy2)
            o2 = iy2 * ec2 + ix2
            t2 = eg2[o2] + (eg2[o2+1] - eg2[o2]) * fx2
            b2 = eg2[o2+ec2] + (eg2[o2+ec2+1] - eg2[o2+ec2]) * fx2
            n2 = t2 + (b2 - t2) * fy2

            # Octave 3
            sx3 = x / es3; sy3 = y / es3
            ix3 = _int(sx3); iy3 = _int(sy3)
            fx3 = sx3 - ix3; fy3 = sy3 - iy3
            fx3 = fx3 * fx3 * (3.0 - 2.0 * fx3)
            fy3 = fy3 * fy3 * (3.0 - 2.0 * fy3)
            o3 = iy3 * ec3 + ix3
            t3 = eg3[o3] + (eg3[o3+1] - eg3[o3]) * fx3
            b3 = eg3[o3+ec3] + (eg3[o3+ec3+1] - eg3[o3+ec3]) * fx3
            n3 = t3 + (b3 - t3) * fy3

            elev = (n0 * w0 + n1 * w1 + n2 * w2 + n3 * w3) * tw

            if elev > 0.62:
                row[x] = CLIFF
            elif elev > 0.58:
                row[x] = CLIFF_EDGE
            else:
                # Detail noise
                sxd = x / ds; syd = y / ds
                ixd = _int(sxd); iyd = _int(syd)
                fxd = sxd - ixd; fyd = syd - iyd
                fxd = fxd * fxd * (3.0 - 2.0 * fxd)
                fyd = fyd * fyd * (3.0 - 2.0 * fyd)
                od = iyd * dc + ixd
                td = dg[od] + (dg[od+1] - dg[od]) * fxd
                bd = dg[od+dc] + (dg[od+dc+1] - dg[od+dc]) * fxd
                detail = td + (bd - td) * fyd

                scatter = hp(s3, x, y) % 1000 * 0.001

                if detail > 0.65 and scatter > 0.92:
                    row[x] = PALM_TREE
                elif detail < 0.35 and scatter > 0.95:
                    row[x] = CACTUS
                elif scatter > 0.985:
                    row[x] = DEAD_BUSH
                elif scatter > 0.975:
                    row[x] = ROCK
                elif detail > 0.55:
                    row[x] = SAND_DARK
                # else: stays SAND (0)

        rows.append(tuple(row))
    return tuple(rows)
