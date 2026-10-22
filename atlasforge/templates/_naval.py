"""Private shared construction for naval templates: gentle beaches, ports and mixed economy."""
import numpy as np
from scipy import ndimage

from .. import SQ
from ..biomes import BIOMES
from ..design import Design
from ..noise import fbm
from ..symmetry import Symmetry, mirror_east_west, mirror_pairs
from ..terrain import ellipse_sdf, grid, plateau
from .base import Param
from .common import biome_param, flatten_all, size_param, sym_fields

LAND_HEIGHT = 100.0
SHIP_DEPTH = 15.0


def naval_params():
    return (
        size_param((12, 14, 16, 18, 20), 16, adv_smallest=8),
        biome_param("temperate"),
        Param("depth", "Sea depth", "int", 180, min=100, max=320, step=10,
              adv_min=40, adv_max=600, help="Depth in elmos below the water surface"),
        Param("beach_slope", "Beach slope", "int", 14, min=10, max=18, step=1,
              adv_min=5, adv_max=40, help="Real slope in degrees between the seabed and dry land"),
        Param("coast_noise", "Coast irregularity", "int", 55, min=0, max=100, step=5,
              adv_max=250, help="Coastline displacement in elmos"),
        Param("sea_metal", "Underwater metal share", "float", 0.65, min=0.3, max=0.8, step=0.05,
              adv_min=0.0, adv_max=1.0, help="Share of expansion spots placed on the seabed"),
        Param("geovents", "Geothermal vents", "bool", True,
              help="Add one geothermal vent on each home island"),
    )


def sea(v, seed):
    n = v["size"] * 64 + 1
    W = (n - 1) * SQ
    rng = np.random.default_rng(seed)
    xx, zz = grid(n)
    ripple = fbm((n, n), rng, base=6, octaves=3)
    edge = fbm((n, n), rng, base=13, octaves=3)
    ripple, edge = sym_fields("ew", ripple, edge)
    edge = (edge - edge.mean()) / (np.max(np.abs(edge - edge.mean())) + 1e-6)
    h = (-v["depth"] + 6 * ripple).astype(np.float32)
    return h, xx, zz, edge, rng, W


def island(h, xx, zz, edge, v, cx, cz, rx, rz):
    plateau(h, ellipse_sdf(xx, zz, cx, cz, rx, rz), LAND_HEIGHT,
            side_deg=v["beach_slope"], noise=edge, amp=v["coast_noise"], toe=36)   # soft valleys between islands


def finish(template, v, h, xx, zz, W, rng, base, port, gates=()):
    """Keep ports explicit: a land start must never be silently snapped into water by checks."""
    sym = Symmetry("ew", W, W)
    h = mirror_east_west(h)
    # Beach flanks from both sides meet at the centre line in a V-shaped underwater crease: round it off.
    # The smoothing is symmetric, so the map stays exactly mirrored.
    band = np.exp(-((xx - W / 2) / 260.0) ** 2) * np.clip((-h - 20) / 30, 0, 1)
    h = (h + band * (ndimage.gaussian_filter(h, 4) - h)).astype(np.float32)
    starts = [base, sym.mirror(*base)]
    ports = [port, sym.mirror(*port)]
    # Select well-separated flat sites, away from beaches and the mirror seam.
    # Pairing resources after selection gives exact equality of position and income.
    from ..terrain import move_slope
    flat = move_slope(h) < 3
    land = (h > 65) & flat
    water = (h < -SHIP_DEPTH - 20) & flat
    land &= ndimage.distance_transform_edt(h > 30) * SQ > 150
    water &= ndimage.distance_transform_edt(h < -SHIP_DEPTH) * SQ > 180
    sea_labels, _ = ndimage.label(h < -SHIP_DEPTH)
    port_label = sea_labels[int(port[1] / SQ), int(port[0] / SQ)]
    water &= (sea_labels == port_label) & (port_label != 0)
    west = []
    # Three nearby safe spots keep opening economy independent of expansion density.
    for dx, dz in ((-170, -220), (-170, 220), (240, 0)):
        x, z = base[0] + dx, base[1] + dz
        west.append((x, z, 2.0))
    count = max(6, round(v["size"] * 1.45))
    sea_count = round(count * v["sea_metal"])
    # Expansion spots are spread evenly (random dart throwing with the largest gap that still fits them)
    # over the west half: away from the map edge, the mirror line, the bases and the ports. Land spots
    # prefer islands other than the home island.
    step = 48.0
    edge = 0.085 * W
    xs = np.arange(edge, W / 2 - 0.04 * W, step)
    zs = np.arange(edge, W - edge, step)
    gx, gz = np.meshgrid(xs, zs)
    gx, gz = gx.ravel(), gz.ravel()
    gi, gj = (gz / SQ).astype(int), (gx / SQ).astype(int)
    land_lab, _ = ndimage.label(h > 30)
    home = land_lab[int(base[1] / SQ), int(base[0] / SQ)]
    fixed = [(x, z) for x, z, _ in west] + [tuple(port)]
    order = rng.permutation(len(gx))

    def throw(mask, wanted, first=None, others=()):
        ok = mask[gi[order], gj[order]]
        idx = order[ok]
        if first is not None:                                       # preferred candidates first
            pref = first[idx]
            idx = np.concatenate([idx[pref], idx[~pref]])
        if wanted <= 0 or not len(idx):
            return []
        gap = W / 12
        while gap >= 260:
            got = []
            pts = fixed + list(others)
            for k in idx:
                x, z = float(gx[k]), float(gz[k])
                if all((x - a) ** 2 + (z - b) ** 2 >= gap * gap for a, b in pts + got) and \
                        (x - base[0]) ** 2 + (z - base[1]) ** 2 >= (gap * 1.4) ** 2:
                    got.append((x, z))
                    if len(got) == wanted:
                        return got
            gap *= 0.9
        return got

    picked = throw(water, sea_count)
    picked += throw(land, count - len(picked), first=land_lab[gi, gj] != home, others=picked)
    for x, z in picked:
        d = np.hypot(x - base[0], z - base[1]) / (W / 2)
        under = h[int(z / SQ), int(x / SQ)] < 0
        west.append((x, z, round(min(3.4, 2.0 + 1.1 * d + (0.2 if under else 0.0)), 2)))
    mexes = mirror_pairs(west, sym)
    geos = [(base[0], base[1] + 420)] if v["geovents"] else []
    geos += [sym.mirror(*p) for p in list(geos)]
    flatten_all(h, starts, mexes, geos)
    h = mirror_east_west(h).astype(np.float32)
    clear = np.zeros(h.shape, bool)
    for x, z in ports:
        clear |= np.hypot(xx - x, zz - z) < 500
    # Protect beaches against erosion so the waterline and landing routes remain stable.
    clear |= h < 60
    biome = dict(BIOMES[v["biome"]], water_damage=0)
    boxes = _base_boxes(starts, W)
    return Design(hm=h, sym=sym, starts=starts, teams=[[starts[0]], [starts[1]]],
                  mexes=mexes, geos=geos, biome=biome, title=template.title,
                  description=template.description, startboxes=boxes, gates=list(gates),
                  tree_block=clear | (h < 20), keep_clear=clear,
                  movement_profile="naval", naval_starts=[[ports[0]], [ports[1]]],
                  marks=[(x, z, "Port", (110, 200, 255)) for x, z in ports],
                  notes=["Naval map: sea crossings and underwater metal use naval validation.",
                         f"Expansion metal sites placed: {len(west) - 3} of {count}"],
                  notes_ok=len(west) - 3 == count)


def _base_boxes(starts, W):
    """Compact base boxes, unlike full strips that include unrelated islands."""
    entries = []
    half = min(430, W * 0.055)
    for side, (x, z) in enumerate(starts):
        name = ("West", "East")[side]
        x0, x1 = max(0, x - half), min(W, x + half)
        z0, z1 = max(0, z - half), min(W, z + half)
        entries.append(f'[{side}] = {{ nameLong = "{name}", nameShort = "{name[0]}", '
                       f'startpoints = {{ {{{x:.0f}, {z:.0f}}} }}, boxes = {{ {{ '
                       f'{{{x0:.0f}, {z0:.0f}}}, {{{x1:.0f}, {z0:.0f}}}, '
                       f'{{{x1:.0f}, {z1:.0f}}}, {{{x0:.0f}, {z1:.0f}}} }} }} }}')
    return "return {\n" + ",\n".join(entries) + "\n}\n"
