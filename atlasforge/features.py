"""Random tree placement (Zero-K feature types treetype0..15)."""
import numpy as np

from . import SQ
from .noise import fbm, norm01
from .terrain import slope_deg


def place_trees(hm, sym, mexes, geos, starts, biome, rng, water_h, keep_clear=None):
    """Symmetric forest patches. keep_clear: optional bool grid (heightmap resolution) without trees,
    e.g. carved ramps. Returns [(type 0..15, x, y, z, rotation)]."""
    if not biome["trees"]:
        return []
    nz, nx = hm.shape
    dens = norm01(fbm(hm.shape, rng, base=nx / 64 * 1.5, octaves=4))
    dens = 0.5 * (dens + sym.mirror_grid(dens))
    sl = slope_deg(hm)
    trees = []
    target = int(nx * nz / 64 * 0.5 * biome["tree_density"])
    W, H = sym.W, sym.H
    blockers = [(m["x"], m["z"], 120) for m in mexes] + [(g[0], g[1], 150) for g in geos] + \
               [(s[0], s[1], 700) for s in starts]
    cell = lambda x, z: (min(nz - 1, int(z / SQ)), min(nx - 1, int(x / SQ)))
    tries = 0
    while len(trees) < target and tries < target * 30:
        tries += 1
        x, z = rng.uniform(40, W - 40), rng.uniform(40, H - 40)
        if sym.side(x, z) >= 0:
            continue
        i, j = cell(x, z)
        if dens[i, j] < 0.62 or sl[i, j] > 20 or hm[i, j] < water_h + 6:
            continue
        mx, mz = sym.mirror(x, z)
        if keep_clear is not None and (keep_clear[i, j] or keep_clear[cell(mx, mz)]):
            continue
        if rng.random() > (dens[i, j] - 0.6) * 3:
            continue
        if any((x - bx) ** 2 + (z - bz) ** 2 < br * br for bx, bz, br in blockers):
            continue
        t = int(rng.integers(0, 16))
        rot = float(rng.uniform(0, 65535))
        trees.append((t, x, float(hm[i, j]), z, rot))
        trees.append((t, mx, float(hm[cell(mx, mz)]), mz, rot))
    return trees
