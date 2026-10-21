"""Shared helpers for templates: base terrain, flattening, D4 symmetry, start box files, common params."""
import math

import numpy as np

from .. import SQ
from ..biomes import BIOMES
from ..noise import fbm, ridged, smoothstep
from ..symmetry import seam_blend
from ..terrain import flatten_disc, grid
from .base import Param

BIOME_CHOICES = tuple(sorted(BIOMES))
H_LOW = 100.0


def size_param(choices, default, adv_smallest=4):
    """adv_smallest: smallest size the template can still build in advanced mode."""
    return Param("size", "Map size", "choice", default, choices=tuple(choices),
                 adv_choices=tuple(range(adv_smallest, 33, 2)),
                 help="Width and height in Spring map units (8 = small 1v1, 16 = 2v2, 20 = large team game)")


def general_params():
    """Settings every template has (applied by forge.make after the template)."""
    return (
        Param("metal", "Metal amount", "float", 1.0, min=0.5, max=2.0, step=0.1, adv_min=0.1, adv_max=5.0,
              group="General", help="Multiplies the value of every metal spot"),
        Param("trees", "Trees", "float", 1.0, min=0.0, max=2.0, step=0.1, adv_max=5.0, group="General",
              help="Tree density (biomes without trees stay bare)"),
        Param("rocks", "Rocks", "float", 0.5, min=0.0, max=2.0, step=0.1, adv_max=6.0, group="General",
              help="Rock clusters with reclaimable metal (glowing crystals on alien and moon maps)"),
        Param("wrecks", "Wrecks", "float", 0.3, min=0.0, max=2.0, step=0.1, adv_max=6.0, group="General",
              help="Battlefield wrecks of Zero-K units between the bases (reclaimable metal)"),
        Param("erosion", "Erosion", "float", 0.6, min=0.0, max=1.5, step=0.1, adv_max=4.0, group="General",
              help="Rain-carved gullies and valleys on natural slopes; bases, metal spots, chokes and walls "
                   "stay as designed"),
    )


def biome_param(default):
    return Param("biome", "Biome", "choice", default, choices=BIOME_CHOICES, help="Colours, sky, light and trees")


def sym_fields(mode, *fields):
    """Noise fields made symmetric with a seamless blend (see symmetry.seam_blend)."""
    out = tuple(seam_blend(f, mode).astype(np.float32) for f in fields)
    return out if len(out) > 1 else out[0]


def base_terrain(n, rng, calm_r, center_x, sym=None):
    """Gentle ground at about H_LOW with hills further than calm_r from the vertical centre line.
    sym: symmetry of the map ("ew", "ns", "point", "d4") - the noise is made symmetric before anything is
    built on it, so the final mirror copy has no seam.
    Returns h, xx, zz, low (normalised fbm), en (edge noise -1..1)."""
    xx, zz = grid(n)
    low = fbm((n, n), rng, base=5, octaves=6); low = (low - low.mean()) / (low.std() + 1e-6)
    hills = ridged((n, n), rng, base=6) ** 2.6
    en = fbm((n, n), rng, base=22, octaves=3); en /= np.abs(en).max() + 1e-6
    if sym:
        low, hills, en = sym_fields(sym, low, hills, en)
    calm = smoothstep(calm_r, calm_r + 900, np.abs(xx - center_x))
    h = (H_LOW + 14 * low + 70 * hills * calm).astype(np.float32)
    return h, xx, zz, low, en


def flatten_all(hm, starts, mexes, geos, start_r=(330, 650)):
    for p in starts:
        flatten_disc(hm, p[0], p[1], start_r[0], start_r[1])
    for m in mexes:
        flatten_disc(hm, m["x"], m["z"], 45, 100)
    for g in geos:
        flatten_disc(hm, g[0], g[1], 55, 110)


# ----------------------------------------------------------------------------- D4 (four bases)
def d4(h):
    """Copy the NW quadrant exactly to NE, SW, SE (square grid, odd size)."""
    n = h.shape[0]
    half = n // 2
    h[:, half + 1:] = h[:, :half][:, ::-1][:, : n - half - 1]
    h[half + 1:, :] = h[:half, :][::-1, :][: n - half - 1, :]
    return h


def d4_points(pts, W):
    """(x, z, ...) in the NW quadrant -> all mirror images, duplicates on the axes removed."""
    out, seen = [], set()
    for p in pts:
        x, z, rest = p[0], p[1], tuple(p[2:])
        for mx in (x, W - x):
            for mz in (z, W - z):
                key = (round(mx), round(mz))
                if key in seen:
                    continue
                seen.add(key)
                out.append((mx, mz) + rest)
    return out


def corners(p, W):
    """NW start point -> (NW, NE, SW, SE)"""
    x, z = p
    return [(x, z), (W - x, z), (x, W - z), (W - x, W - z)]


def _q(p, half, W):
    return "{ {%d, %d}, {%d, %d}, {%d, %d}, {%d, %d} }" % (
        max(0, p[0] - half), max(0, p[1] - half), min(W, p[0] + half), max(0, p[1] - half),
        min(W, p[0] + half), min(W, p[1] + half), max(0, p[0] - half), min(W, p[1] + half))


def _sp(ps):
    return ", ".join("{%d, %d}" % (round(x), round(z)) for x, z in ps)


def four_base_boxes(team0, team1, names0, names1, W, half=900):
    """2 teams with two bases each, or one base per team when 3-4 teams play (FFA).
    team0/team1: two start points each; names: (long, short) per base."""
    a, b = team0
    c, d = team1
    return f"""-- Atlas Map Forge: 2 teams -> two bases each; 3-4 teams -> one base per team (FFA)
if GetTeamCount and GetTeamCount() <= 2 then
\treturn {{
\t\t[0] = {{ nameLong = "{names0[0]}", nameShort = "{names0[1]}", startpoints = {{ {_sp([a, b])} }}, boxes = {{ {_q(a, half, W)}, {_q(b, half, W)} }} }},
\t\t[1] = {{ nameLong = "{names1[0]}", nameShort = "{names1[1]}", startpoints = {{ {_sp([c, d])} }}, boxes = {{ {_q(c, half, W)}, {_q(d, half, W)} }} }},
\t}}
end
return {{
\t[0] = {{ nameLong = "Base 1", nameShort = "1", startpoints = {{ {_sp([a])} }}, boxes = {{ {_q(a, half, W)} }} }},
\t[1] = {{ nameLong = "Base 2", nameShort = "2", startpoints = {{ {_sp([c])} }}, boxes = {{ {_q(c, half, W)} }} }},
\t[2] = {{ nameLong = "Base 3", nameShort = "3", startpoints = {{ {_sp([b])} }}, boxes = {{ {_q(b, half, W)} }} }},
\t[3] = {{ nameLong = "Base 4", nameShort = "4", startpoints = {{ {_sp([d])} }}, boxes = {{ {_q(d, half, W)} }} }},
}}
"""


def coop_boxes(player_box, enemy_box, players):
    """Co-op (chicken) maps: players in one box, the chicken side in another."""
    f = lambda pts: ", ".join("{%d, %d}" % (round(x), round(z)) for x, z in pts)
    q = lambda b: "{ {%d, %d}, {%d, %d}, {%d, %d}, {%d, %d} }" % (b[0], b[1], b[2], b[1], b[2], b[3], b[0], b[3])
    cx, cz = (enemy_box[0] + enemy_box[2]) / 2, (enemy_box[1] + enemy_box[3]) / 2
    return f"""return {{
\t[0] = {{ nameLong = "Players", nameShort = "P", startpoints = {{ {f(players)} }}, boxes = {{ {q(player_box)} }} }},
\t[1] = {{ nameLong = "Chickens", nameShort = "C", startpoints = {{ {{{cx:.0f}, {cz:.0f}}} }}, boxes = {{ {q(enemy_box)} }} }},
}}
"""


def polar(c, r, ang_deg):
    a = math.radians(ang_deg)
    return c + r * math.cos(a), c + r * math.sin(a)


def disc_mask(xx, zz, x, z, r):
    return np.hypot(xx - x, zz - z) < r


def cell(p):
    return int(p[1] / SQ), int(p[0] / SQ)
