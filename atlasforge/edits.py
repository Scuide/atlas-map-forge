"""Manual edits of a finished design (editor stage A): metal spots, geovents and start points.

A map is (template, settings, seed) plus a list of edits that is applied to the finished Design. The terrain
is not recomputed, so forge.make() stays deterministic and undo/redo is just a shorter list.

Edit entries (one per user action, positions in elmos, address the object the user clicked):
    {"op": "move_mex",  "from": [x, z], "to": [x, z]}
    {"op": "add_mex",   "at": [x, z], "metal": 2.0}
    {"op": "del_mex",   "at": [x, z]}
    {"op": "set_metal", "at": [x, z], "metal": 3.0}
    {"op": "move_geo" | "add_geo" | "del_geo", ...}        (as for mexes, no metal)
    {"op": "move_start", "from": [x, z], "to": [x, z]}    (the number of players comes from the template)
    {"op": "set_box", "team": k, "poly": i, "points": [[x, z], ...]}   (polygon i of team k's start box, 3+ points)
    {"op": "brush", "tool": "raise"|"lower"|"flatten"|"smooth", "at": [x, z], "radius": r, "strength": s,
     "amount": a, "target": h}   (terrain brush from brushes.py; amount for raise/lower, target for flatten only)
    {"op": "brush", "tool": "ramp", "at": [x, z], "to": [x, z], "radius": w, "strength": s}
     (ramp from A = at to B = to, width w: heights go linearly from the ground at A to the ground at B)
    {"op": "brush", "tool": "noise", "at": [x, z], "radius": r, "strength": s, "amount": a, "seed": k}
     (roughen: random heights of +-amount from seed k, same pattern at every mirror image)
    {"op": "brush", "tool": "terrace", "at": [x, z], "radius": r, "strength": s, "amount": h}
     (snap heights to steps of h elmos, amount is the terrace height and must be above 0)
    {"op": "stamp", "src": [x0, z0, x1, z1], "to": [x, z], "rotate": 0|90|180|270, "flip": f, "blend": b}
     (copy the heights of the rectangle src, earlier edits included, and paste them centred on to, turned
     clockwise, mirrored left-right first when flip, with a soft edge of b elmos; blend 0 copies them exactly)
    {"op": "paint", "material": "path"|"concrete"|"scorch"|"lava", "points": [[x, z], ...], "radius": r,
     "strength": s}   (texture stroke along the polyline, soft edge; only the look changes, lava is cosmetic)
    {"op": "paint", "material": m, "fill": "poly", "points": [[x, z], ...], "strength": s}   (polygon of 3+ points)
    {"op": "paint", "material": m, "fill": "band", "low": a, "high": b, "at": [x, z], "strength": s}
     (all ground from height a to b; with at only the connected patch under the click and its mirror images)
     material "erase" takes the paint of every layer away under the stroke or fill
    {"op": "features", "kind": "trees"|"rocks"|"wrecks", "mode": "add"|"remove", "at": [x, z], "radius": r,
     "density": d}   (features in a disc: remove takes out the features of that kind in it, add places them on
     dry, flat ground; rocks add their models to the archive when the map has none)

Any edit may carry "enabled": false; it stays in the list (and the project file) but is not applied.

Objects are found by position (nearest within TOL elmos), not by index, so edits stay meaningful after the
settings change. With symmetry on, an edit acts on the whole orbit of the clicked object (mirror image, or the
N rotations of a free-for-all map). Edits that cannot be applied are returned as problems, never raised.
"""
import dataclasses
import math

import numpy as np

from . import SQ
from .decor import WRECKS_GIANT, WRECKS_LARGE, WRECKS_MEDIUM, WRECKS_SMALL
from .symmetry import RotSymmetry, match_orbit, orbit, orbit_degenerate
from .terrain import slope_deg

TOL = 24.0            # elmos: how far from an object a click may be to address it
MIN_GAP = 40.0        # elmos: closest allowed distance between two metal spots / geovents

OPS = ("move_mex", "add_mex", "del_mex", "set_metal", "move_geo", "add_geo", "del_geo", "move_start", "set_box",
       "brush", "stamp", "paint", "features")
BRUSHES = ("raise", "lower", "flatten", "smooth", "ramp", "noise", "terrace")
FEATURE_KINDS = ("trees", "rocks", "wrecks")
FEATURE_MODES = ("add", "remove")
TREE_GAP = 40.0       # elmos: closest allowed distance between two added trees
FEATURE_AREA = {"trees": 1600.0, "rocks": 40000.0, "wrecks": 160000.0}   # elmos^2 per object at density 1
FEATURE_SLOPE = {"trees": 20, "rocks": 30, "wrecks": 16}                # degrees, as decor.place
# rocks as models.feature_pack names them (forge_rock_<size index><variant>), weights as decor.place
ROCK_SIZES = (14, 26, 42, 64)
ROCK_NAMES = [f"forge_rock_{k}{v}" for k in range(len(ROCK_SIZES)) for v in range(2)]
ROCK_WEIGHTS = np.array([0.38, 0.38, 0.27, 0.27, 0.1, 0.1, 0.035, 0.035])
# unit wrecks as decor.place picks them (the giant ones are left to the generator)
WRECK_RADIUS = {n: r for n, _m, r in WRECKS_SMALL + WRECKS_MEDIUM + WRECKS_LARGE + WRECKS_GIANT}
WRECK_POOL = [n for n, _m, _r in WRECKS_SMALL + WRECKS_MEDIUM + WRECKS_LARGE]


def copy_design(d):
    """Cheap copy for editing: the heightmap and masks are shared, only the editable lists are copied."""
    return dataclasses.replace(
        d, mexes=[dict(m) for m in d.mexes], geos=[tuple(g) for g in d.geos],
        starts=[tuple(p) for p in d.starts], teams=[[tuple(p) for p in t] for t in d.teams], notes=list(d.notes),
        features=list(d.features), extra_files=dict(d.extra_files))


def side_of(sym, x, z):
    """Side (or player index on free-for-all maps) a spot belongs to."""
    if isinstance(sym, RotSymmetry):
        return sym.sector(x, z)
    return 0 if sym.side(x, z) < 0 else 1


def _pt(v, name):
    if not isinstance(v, (list, tuple)) or len(v) != 2 or not all(
            isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in v):
        raise ValueError(f"{name}: expected [x, z]")
    return float(v[0]), float(v[1])


def _nearest(points, p, tol=TOL, skip=()):
    best, bd = None, tol
    for i, q in enumerate(points):
        if i in skip:
            continue
        dd = math.hypot(q[0] - p[0], q[1] - p[1])
        if dd <= bd:
            best, bd = i, dd
    return best


def _inside(sym, p):
    return 0 <= p[0] <= sym.W and 0 <= p[1] <= sym.H


def _targets(sym, p, on):
    """Positions an edit at p touches: the whole orbit (symmetry on) or only p."""
    return orbit(sym, p[0], p[1]) if on else [p]


def _collides(points, others_skip, spots):
    """Does any of spots come closer than MIN_GAP to a point of points (ignoring indices in others_skip)?"""
    for s in spots:
        for i, q in enumerate(points):
            if i not in others_skip and math.hypot(q[0] - s[0], q[1] - s[1]) < MIN_GAP:
                return True
    for i, s in enumerate(spots):                           # the orbit points against each other
        if any(math.hypot(t[0] - s[0], t[1] - s[1]) < MIN_GAP for t in spots[i + 1:]):
            return True
    return False


def _orbit_ok(sym, p, on):
    if on and orbit_degenerate(sym, p[0], p[1]):
        return "on the symmetry axis or at the centre: it has no mirror image (turn symmetry off to place it there)"
    return None


def _matches(sym, ref, points, on):
    """Indices (original first) of the objects belonging to ref's orbit. The first entry must exist."""
    if not on:
        i = _nearest(points, ref)
        return [] if i is None else [i]
    hits = match_orbit(sym, ref, points, tol=TOL)
    if hits[0] is None:
        return []
    out = []
    for h in hits:
        if h is not None and h not in out:
            out.append(h)
    return out


def apply_edits(design, edits, symmetry=True):
    """-> (edited copy of design, problems). problems: [{"index", "edit", "reason"}] for edits not applied
    (object not found = orphaned, or the result would break the map). The input design is not modified."""
    d = copy_design(design)
    sym = d.sym
    problems = []

    def fail(i, e, why):
        problems.append(dict(index=i, edit=e, reason=why))

    for i, e in enumerate(edits or []):
        if isinstance(e, dict) and e.get("enabled", True) is False:
            continue                                       # switched off in the edit list
        try:
            _apply_one(d, sym, e, symmetry, lambda why, i=i, e=e: fail(i, e, why))
        except ValueError as ex:
            fail(i, e, str(ex))
    return d, problems


def _apply_one(d, sym, e, on, fail):
    op = e.get("op") if isinstance(e, dict) else None
    if op not in OPS:
        return fail("unknown edit")
    if op == "set_box":
        return _set_box(d, sym, e, on, fail)
    if op == "brush":
        return _brush(d, sym, e, on, fail)
    if op == "stamp":
        return _stamp(d, sym, e, on, fail)
    if op == "paint":
        return _paint(d, sym, e, on, fail)
    if op == "features":
        return _features(d, sym, e, on, fail)
    kind = op.split("_")[1] if op != "set_metal" else "mex"
    verb = op.split("_")[0] if op != "set_metal" else "set"
    if kind == "mex":
        pts = d.mexes
    elif kind == "geo":
        pts = d.geos
    else:
        pts = d.starts
    xy = [(p["x"], p["z"]) for p in pts] if kind == "mex" else pts

    if verb == "add":
        at = _pt(e.get("at"), "at")
        spots = _targets(sym, at, on)
        if not all(_inside(sym, s) for s in spots):
            return fail("outside the map")
        why = _orbit_ok(sym, at, on)
        if why:
            return fail(why)
        if _collides(list(xy) + [(g[0], g[1]) for g in d.geos if kind == "mex"] +
                     [(m["x"], m["z"]) for m in d.mexes if kind == "geo"], (), spots):
            return fail("too close to another metal spot or geovent")
        for s in spots:
            if kind == "mex":
                m = float(e.get("metal", 2.0))
                d.mexes.append(dict(x=float(s[0]), z=float(s[1]), metal=m, side=side_of(sym, *s)))
            else:
                d.geos.append((float(s[0]), float(s[1])))
        return None

    src = _pt(e.get("at" if verb in ("del", "set") else "from"), "at" if verb in ("del", "set") else "from")
    idx0 = _nearest(xy, src)
    if idx0 is None:
        return fail("nothing there (the map changed since this edit was made)")
    ref = xy[idx0]
    hit = _matches(sym, ref, xy, on)
    if not hit:
        return fail("nothing there (the map changed since this edit was made)")

    if verb == "set":
        m = float(e.get("metal", 0))
        if not m > 0:
            return fail("metal must be positive")
        for h in hit:
            d.mexes[h]["metal"] = m
        return None

    if verb == "del":
        if kind == "start":
            return fail("start points cannot be deleted")
        for h in sorted(hit, reverse=True):
            del (d.mexes if kind == "mex" else d.geos)[h]
        return None

    # move
    to = _pt(e.get("to"), "to")
    if on:
        why = _orbit_ok(sym, to, on) or (orbit_degenerate(sym, ref[0], ref[1]) and _orbit_ok(sym, ref, on))
        if why:
            return fail(why)
    orb_to = _targets(sym, to, on)
    if on and len(hit) > 1:                                   # keep each partner paired with its own image
        pairs = match_orbit(sym, ref, xy, tol=TOL)
        moves = [(h, orb_to[k]) for k, h in enumerate(pairs) if h is not None]
    else:
        moves = [(hit[0], to)]
    if not all(_inside(sym, t) for _, t in moves):
        return fail("outside the map")
    if kind != "start":
        skip = {h for h, _ in moves}
        others = [p for j, p in enumerate(xy) if j not in skip]
        extra = [(g[0], g[1]) for g in d.geos] if kind == "mex" else [(m["x"], m["z"]) for m in d.mexes]
        if _collides(others + extra, (), [t for _, t in moves]):
            return fail("too close to another metal spot or geovent")
    if kind == "mex":
        for h, t in moves:
            d.mexes[h].update(x=float(t[0]), z=float(t[1]), side=side_of(sym, *t))
    elif kind == "geo":
        for h, t in moves:
            d.geos[h] = (float(t[0]), float(t[1]))
    else:
        for h, t in moves:
            old, new = d.starts[h], (float(t[0]), float(t[1]))
            d.starts[h] = new
            for team in d.teams:
                for j, q in enumerate(team):
                    if tuple(q) == tuple(old):
                        team[j] = new
    return None


def brush_params(e):
    """Validated (tool, at, radius, strength, amount, target, to, seed) of a brush edit; ValueError when malformed.
    to is the end point B of a ramp, seed the pattern of noise (0 when absent); None for the other tools."""
    tool = e.get("tool")
    if tool not in BRUSHES:
        raise ValueError(f"tool: expected one of {', '.join(BRUSHES)}")
    at = _pt(e.get("at"), "at")
    radius = e.get("radius")
    if not isinstance(radius, (int, float)) or isinstance(radius, bool) or not math.isfinite(radius) or radius <= 0:
        raise ValueError("radius: expected a number > 0")
    strength = e.get("strength", 1.0)
    if not isinstance(strength, (int, float)) or isinstance(strength, bool) or not 0 <= strength <= 1:
        raise ValueError("strength: expected a number from 0 to 1")
    amount = e.get("amount", 20.0)
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not math.isfinite(amount):
        raise ValueError("amount: expected a number")
    target = e.get("target")
    if tool == "terrace" and amount <= 0:
        raise ValueError("amount: the terrace height, above 0")
    seed = e.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed: expected an integer from 0")
    if "seed" in e and tool != "noise":
        raise ValueError("seed: for noise only")
    if target is not None and (tool != "flatten" or not isinstance(target, (int, float)) or isinstance(target, bool)
                               or not math.isfinite(target)):
        raise ValueError("target: a number, for flatten only")
    to = None
    if tool == "ramp":
        to = _pt(e.get("to"), "to")
    elif e.get("to") is not None:
        raise ValueError("to: for ramp only")
    return (tool, at, float(radius), float(strength), float(amount),
            None if target is None else float(target), to, seed)


def _brush(d, sym, e, on, fail):
    """Apply a terrain brush (brushes.py) at a point, mirrored or rotated over its orbit when symmetry is on.
    The height map is replaced by a new array; the edit list itself is the undo history."""
    from . import brushes

    tool, at, radius, strength, amount, target, to, seed = brush_params(e)
    spots = _targets(sym, at, on)
    if not all(_inside(sym, s) for s in spots):
        return fail("outside the map")
    why = _orbit_ok(sym, at, on)
    if why:
        return fail(why)
    if tool == "ramp":                                      # A_k -> B_k pairs the same rotation or mirror on both ends
        ends = _targets(sym, to, on)
        if not all(_inside(sym, s) for s in ends):
            return fail("outside the map")
        why = _orbit_ok(sym, to, on)
        if why:
            return fail(why)
        if tuple(at) == tuple(to):
            return fail("a ramp needs two different points")
        hm = d.hm
        for (ax, az), (bx, bz) in zip(spots, ends):
            hm = brushes.ramp(hm, ax, az, bx, bz, radius, strength)
        d.hm = hm
        return None
    if tool == "flatten" and target is None:                # one height for the whole orbit, the clicked ground's
        iz, ix = brushes._centre(d.hm, at[0], at[1])
        target = float(d.hm[iz, ix])
    hm = d.hm
    for cx, cz in spots:
        if tool == "raise":
            hm = brushes.raise_(hm, cx, cz, radius, strength, amount)
        elif tool == "lower":
            hm = brushes.lower(hm, cx, cz, radius, strength, amount)
        elif tool == "flatten":
            hm = brushes.flatten(hm, cx, cz, radius, strength, target)
        elif tool == "noise":
            hm = brushes.noise_(hm, cx, cz, radius, strength, amount, seed)
        elif tool == "terrace":
            hm = brushes.terrace(hm, cx, cz, radius, strength, amount)
        else:
            hm = brushes.smooth(hm, cx, cz, radius, strength)
    d.hm = hm
    return None


STAMP_ROTATIONS = (0, 90, 180, 270)
STAMP_MIN_CELLS = 2                     # grid cells per side of the source rectangle, at least


def stamp_params(e):
    """Validated (src, to, rotate, flip, blend) of a stamp edit; ValueError when malformed. src = (x0, z0, x1, z1)
    with x0 < x1 and z0 < z1 (corners may come in any order), to = centre of the pasted copy, rotate in degrees
    clockwise as seen on the map, flip = mirror left-right before rotating, blend = width of the soft edge in elmos."""
    src = e.get("src")
    if not (isinstance(src, (list, tuple)) and len(src) == 4 and all(_num(c) for c in src)):
        raise ValueError("src: expected [x0, z0, x1, z1]")
    x0, x1 = sorted((float(src[0]), float(src[2])))
    z0, z1 = sorted((float(src[1]), float(src[3])))
    if x1 - x0 < STAMP_MIN_CELLS * SQ or z1 - z0 < STAMP_MIN_CELLS * SQ:
        raise ValueError(f"src: the rectangle must be at least {STAMP_MIN_CELLS * SQ} elmos on each side")
    to = _pt(e.get("to"), "to")
    rotate = e.get("rotate", 0)
    if rotate not in STAMP_ROTATIONS or isinstance(rotate, bool):
        raise ValueError("rotate: expected 0, 90, 180 or 270")
    flip = e.get("flip", False)
    if not isinstance(flip, bool):
        raise ValueError("flip: expected true or false")
    blend = e.get("blend", 0.0)
    if not _num(blend) or blend < 0:
        raise ValueError("blend: expected a number from 0")
    return (x0, z0, x1, z1), to, int(rotate), flip, float(blend)


def stamp_patch(hm, src, rotate, flip, blend):
    """-> (heights, weights) of the stamp cut from hm: the cells inside src, mirrored left-right when flip, turned
    rotate degrees clockwise (z grows downwards, so clockwise on the map), and a weight per cell that rises
    smoothly from 0 at the patch border to 1 at blend elmos inside (1 everywhere for blend 0)."""
    from .noise import smoothstep

    x0, z0, x1, z1 = src
    i0, i1 = max(0, int(math.ceil(z0 / SQ))), min(hm.shape[0] - 1, int(math.floor(z1 / SQ)))
    j0, j1 = max(0, int(math.ceil(x0 / SQ))), min(hm.shape[1] - 1, int(math.floor(x1 / SQ)))
    patch = np.array(hm[i0:i1 + 1, j0:j1 + 1], np.float64)
    if flip:
        patch = patch[:, ::-1]
    patch = np.rot90(patch, -(rotate // 90))                     # rot90 turns counter-clockwise on screen (z down)
    h, w = patch.shape
    if blend <= 0:
        return patch, np.ones((h, w))
    a = np.arange(h)[:, None]
    b = np.arange(w)[None, :]
    edge = np.minimum(np.minimum(a, h - 1 - a), np.minimum(b, w - 1 - b)) * SQ
    return patch, smoothstep(0.0, blend, edge.astype(np.float64))


def _stamp(d, sym, e, on, fail):
    """Copy the heights of a rectangle (with all earlier edits) and paste them centred on a point, turned and
    mirrored as asked, with a soft edge of blend elmos. With symmetry on the pasted copy is mirrored (rotated) to
    every side like the other terrain edits; parts beyond the map border are cut off."""
    src, to, rotate, flip, blend = stamp_params(e)
    if not (_inside(sym, src[:2]) and _inside(sym, src[2:])):
        return fail("the copied rectangle is outside the map")
    if not _inside(sym, to):
        return fail("outside the map")
    why = _orbit_ok(sym, to, on)
    if why:
        return fail(why)
    hm = np.asarray(d.hm)
    patch, wgt = stamp_patch(hm, src, rotate, flip, blend)
    h, w = patch.shape
    ti = int(round(to[1] / SQ - (h - 1) / 2))                    # top-left cell of the pasted copy
    tj = int(round(to[0] / SQ - (w - 1) / 2))
    a0, a1 = max(0, ti), min(hm.shape[0], ti + h)
    b0, b1 = max(0, tj), min(hm.shape[1], tj + w)
    if a1 <= a0 or b1 <= b0:
        return fail("outside the map")
    vals = np.zeros(hm.shape)                                    # the copy on the full grid, weight 0 elsewhere
    mask = np.zeros(hm.shape)
    vals[a0:a1, b0:b1] = patch[a0 - ti:a1 - ti, b0 - tj:b1 - tj]
    mask[a0:a1, b0:b1] = wgt[a0 - ti:a1 - ti, b0 - tj:b1 - tj]
    images = [(vals, mask)]
    if on:
        if isinstance(sym, RotSymmetry):
            images += [(sym.rotate_grid(vals, k), sym.rotate_grid(mask, k)) for k in range(1, sym.n)]
        else:
            images.append((sym.mirror_grid(vals), sym.mirror_grid(mask)))
    out = hm.astype(np.float64)
    for v, m in images:
        out = out * (1 - m) + v * m
    d.hm = out.astype(hm.dtype)
    return None


PAINT_MATERIALS = ("path", "concrete", "scorch", "lava", "erase")     # erase takes paint away instead of adding it
PAINT_FILLS = ("poly", "band")
PAINT_MAX_POINTS = 400


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def paint_params(e):
    """Validated dict(material, fill, points, radius, strength, low, high, at) of a paint edit; ValueError when
    malformed. fill None = stroke along points (radius needed); "poly" = the polygon of 3+ points filled;
    "band" = the ground from height low to high, only the connected patch under at (and its images) when at is set."""
    material = e.get("material")
    if material not in PAINT_MATERIALS:
        raise ValueError(f"material: expected one of {', '.join(PAINT_MATERIALS)}")
    fill = e.get("fill")
    if fill is not None and fill not in PAINT_FILLS:
        raise ValueError(f"fill: expected one of {', '.join(PAINT_FILLS)}")
    strength = e.get("strength", 1.0)
    if not isinstance(strength, (int, float)) or isinstance(strength, bool) or not 0 < strength <= 1:
        raise ValueError("strength: expected a number above 0 up to 1")
    out = dict(material=material, fill=fill, points=None, radius=None, strength=float(strength),
               low=None, high=None, at=None)
    if fill == "band":
        low, high = e.get("low"), e.get("high")
        if not (_num(low) and _num(high) and low <= high):
            raise ValueError("low, high: expected two heights, low not above high")
        out.update(low=float(low), high=float(high))
        if e.get("at") is not None:
            out["at"] = _pt(e.get("at"), "at")
        return out
    pts = e.get("points")
    lo = 3 if fill == "poly" else 1
    if not isinstance(pts, list) or not lo <= len(pts) <= PAINT_MAX_POINTS:
        raise ValueError(f"points: {lo} to {PAINT_MAX_POINTS} [x, z] points")
    out["points"] = [_pt(p, "points") for p in pts]
    if fill is None:
        radius = e.get("radius")
        if not _num(radius) or radius <= 0:
            raise ValueError("radius: expected a number > 0")
        out["radius"] = float(radius)
    return out


def paint_stroke(shape, points, radius, strength):
    """Soft 0..1 coverage of a stroke (polyline of points in elmos, round brush) on a heightmap grid of the given shape."""
    from . import SQ
    from .noise import smoothstep
    import numpy as np

    x0 = min(p[0] for p in points) - radius
    x1 = max(p[0] for p in points) + radius
    z0 = min(p[1] for p in points) - radius
    z1 = max(p[1] for p in points) + radius
    j0, j1 = max(0, int(x0 / SQ)), min(shape[1], int(x1 / SQ) + 2)
    i0, i1 = max(0, int(z0 / SQ)), min(shape[0], int(z1 / SQ) + 2)
    cov = np.zeros(shape, np.float32)
    if j1 <= j0 or i1 <= i0:
        return cov
    gx = (np.arange(j0, j1, dtype=np.float32) * SQ)[None, :]
    gz = (np.arange(i0, i1, dtype=np.float32) * SQ)[:, None]
    dist = np.full((i1 - i0, j1 - j0), np.inf, np.float32)
    segs = list(zip(points, points[1:])) or [(points[0], points[0])]
    for (ax, az), (bx, bz) in segs:
        vx, vz = bx - ax, bz - az
        ll = vx * vx + vz * vz
        t = np.clip(((gx - ax) * vx + (gz - az) * vz) / ll, 0, 1) if ll > 0 else 0.0
        dist = np.minimum(dist, np.hypot(gx - (ax + t * vx), gz - (az + t * vz)))
    cov[i0:i1, j0:j1] = (1 - smoothstep(0.55 * radius, radius, dist)) * strength
    return cov


def paint_polygon(shape, points, strength):
    """0/strength coverage of the grid points inside a polygon (points in elmos, even-odd rule)."""
    cov = np.zeros(shape, np.float32)
    xs, zs = [p[0] for p in points], [p[1] for p in points]
    j0, j1 = max(0, int(min(xs) / SQ)), min(shape[1], int(max(xs) / SQ) + 2)
    i0, i1 = max(0, int(min(zs) / SQ)), min(shape[0], int(max(zs) / SQ) + 2)
    if j1 <= j0 or i1 <= i0:
        return cov
    gx = (np.arange(j0, j1, dtype=np.float64) * SQ)[None, :]
    gz = (np.arange(i0, i1, dtype=np.float64) * SQ)[:, None]
    inside = np.zeros((i1 - i0, j1 - j0), bool)
    for (ax, az), (bx, bz) in zip(points, points[1:] + points[:1]):
        if az == bz:
            continue
        crosses = (az > gz) != (bz > gz)                           # edge spans the row
        xc = ax + (gz - az) * (bx - ax) / (bz - az)
        inside ^= crosses & (gx < xc)
    cov[i0:i1, j0:j1] = inside * strength
    return cov


def paint_band(hm, low, high, strength, seeds=None):
    """strength on the ground from height low to high; with seeds (grid cells) only the connected patches that
    contain one of them. -> (coverage, hit) where hit says whether any seed lay in the band."""
    from scipy import ndimage

    band = (hm >= low) & (hm <= high)
    if seeds is None:
        return band * np.float32(strength), bool(band.any())
    lab, _n = ndimage.label(band)
    ids = {int(lab[i, j]) for i, j in seeds if lab[i, j]}
    if not ids:
        return np.zeros(hm.shape, np.float32), False
    return np.isin(lab, sorted(ids)) * np.float32(strength), True


def _cell_of(shape, p):
    return (min(shape[0] - 1, max(0, int(round(p[1] / SQ)))), min(shape[1] - 1, max(0, int(round(p[0] / SQ)))))


def _paint(d, sym, e, on, fail):
    """Paint ground texture (paths, concrete, scorch marks, lava crust) over the design's paint layers: a stroke,
    a filled polygon or a height band. With symmetry on, strokes and polygons are mirrored (rotated) as a whole and
    a band fill takes the patch under every image of the click. Lava is cosmetic: it does not hurt units.
    The material erase takes paint of every layer away where the stroke or fill covers the ground."""
    P = paint_params(e)
    shape = d.hm.shape
    if P["fill"] == "band":
        seeds = None
        if P["at"] is not None:
            if not _inside(sym, P["at"]):
                return fail("outside the map")
            seeds = [_cell_of(shape, s) for s in _targets(sym, P["at"], on) if _inside(sym, s)]
        cov, hit = paint_band(d.hm, P["low"], P["high"], P["strength"], seeds)
        if not hit:
            return fail("the ground there is not between the two heights")
    else:
        pts = P["points"]
        if not all(_inside(sym, p) for p in pts):
            return fail("outside the map")
        images = list(zip(*[_targets(sym, p, on) for p in pts]))  # image k of every point = stroke (polygon) k
        cov = np.zeros(shape, np.float32)
        for img in images:
            part = (paint_polygon(shape, list(img), P["strength"]) if P["fill"] == "poly"
                    else paint_stroke(shape, list(img), P["radius"], P["strength"]))
            cov = np.maximum(cov, part)
    layers = dict(d.paint or {})                                    # new dict + new arrays: the original stays untouched
    if P["material"] == "erase":
        if not layers:
            return None
        keep = 1 - cov
        for k, a in layers.items():
            if a is not None:
                layers[k] = np.asarray(a, np.float32) * keep
    else:
        cur = layers.get(P["material"])
        layers[P["material"]] = cov if cur is None else np.maximum(np.asarray(cur, np.float32), cov)
    d.paint = layers
    return None


def feature_params(e):
    """Validated (kind, mode, at, radius, density) of a features edit; ValueError when malformed."""
    kind = e.get("kind", "trees")
    if kind not in FEATURE_KINDS:
        raise ValueError(f"kind: expected one of {', '.join(FEATURE_KINDS)}")
    mode = e.get("mode")
    if mode not in FEATURE_MODES:
        raise ValueError("mode: expected add or remove")
    at = _pt(e.get("at"), "at")
    radius = e.get("radius")
    if not isinstance(radius, (int, float)) or isinstance(radius, bool) or not math.isfinite(radius) or radius <= 0:
        raise ValueError("radius: expected a number > 0")
    density = e.get("density", 0.5)
    if not isinstance(density, (int, float)) or isinstance(density, bool) or not 0 <= density <= 1:
        raise ValueError("density: expected a number from 0 to 1")
    return kind, mode, at, float(radius), float(density)


def _is_kind(name, kind):
    """Whether a feature name belongs to a kind: trees, rocks (crystals too) or wrecks (all other names)."""
    if kind == "trees":
        return name.startswith("treetype")
    if kind == "rocks":
        return name.startswith(("forge_rock_", "forge_crystal_"))
    return not name.startswith(("treetype", "forge_"))


def _features(d, sym, e, on, fail):
    """Add or remove trees, rocks or wrecks in a disc. Remove takes out the features of that kind in the disc (trees
    are also blocked there); add places them at seeded random spots, each with its whole orbit, so the layout stays
    symmetric."""
    kind, mode, at, radius, density = feature_params(e)
    spots = _targets(sym, at, on)
    if not all(_inside(sym, s) for s in spots):
        return fail("outside the map")
    why = _orbit_ok(sym, at, on)
    if why:
        return fail(why)
    if mode == "remove":
        _remove_features(d, spots, radius, kind)
    else:
        _add_features(d, sym, at, radius, density, on, kind)
    return None


def _remove_features(d, spots, r, kind):
    if kind == "trees":
        nz, nx = d.hm.shape
        tb = np.zeros(d.hm.shape, bool) if d.tree_block is None else d.tree_block.copy()
        for cx, cz in spots:
            i0, i1 = max(0, int((cz - r) / SQ)), min(nz - 1, int((cz + r) / SQ) + 1)
            j0, j1 = max(0, int((cx - r) / SQ)), min(nx - 1, int((cx + r) / SQ) + 1)
            ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
            inside = np.hypot(ii * SQ - cz, jj * SQ - cx) <= r
            tb[ii[inside], jj[inside]] = True
        d.tree_block = tb
    d.features = [f for f in d.features
                  if not (_is_kind(f[0], kind) and any(math.hypot(f[1] - cx, f[2] - cz) <= r for cx, cz in spots))]


def _feature_radius(name):
    """Footprint radius of a placed feature, used to keep features apart: trees TREE_GAP / 2 each, rocks and wrecks
    their own size (crystals approximately)."""
    if name.startswith("treetype"):
        return TREE_GAP / 2
    if name.startswith("forge_rock_"):
        return ROCK_SIZES[int(name[len("forge_rock_")])] * 1.2
    return WRECK_RADIUS.get(name, 40.0)


def _add_features(d, sym, at, radius, density, on, kind):
    """Plant about density * one object per FEATURE_AREA[kind] elmos^2 in the disc, on ground no steeper than
    FEATURE_SLOPE[kind] degrees and above the water line, away from metal, geovents and start points. Trees keep
    TREE_GAP between each other; rocks and wrecks keep clear of each other and block the trees growing through
    them. The seed comes from the design and the spot."""
    n = int(round(density * math.pi * radius * radius / FEATURE_AREA[kind]))
    if n <= 0:
        return
    rng = np.random.default_rng([int(d.seed), int(round(at[0])), int(round(at[1])), n])
    hm = d.hm
    nz, nx = hm.shape
    sl = slope_deg(hm)
    blockers = [(m["x"], m["z"], 120) for m in d.mexes] + [(g[0], g[1], 150) for g in d.geos] + \
               [(s[0], s[1], 700) for s in d.starts]
    # trees keep apart from trees; rocks and wrecks from every other rock and wreck (not from the trees)
    obstacles = [(f[1], f[2], _feature_radius(f[0])) for f in d.features if _is_kind(f[0], "trees") == (kind == "trees")]
    added = []
    tries = 0
    count = 0
    while count < n and tries < n * 30:
        tries += 1
        a, rr = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.uniform())
        x, z = at[0] + rr * math.cos(a), at[1] + rr * math.sin(a)
        if not (0 <= x <= sym.W and 0 <= z <= sym.H):
            continue
        i, j = min(nz - 1, int(z / SQ)), min(nx - 1, int(x / SQ))
        if hm[i, j] < 6 or sl[i, j] > FEATURE_SLOPE[kind]:
            continue
        copies = [c for c in _targets(sym, (x, z), on) if _inside(sym, c)]
        if any(math.hypot(cx - bx, cz - bz) < br for cx, cz in copies for bx, bz, br in blockers):
            continue
        if kind == "trees":
            name = f"treetype{int(rng.integers(0, 16))}"
        elif kind == "rocks":
            name = ROCK_NAMES[int(rng.choice(len(ROCK_NAMES), p=ROCK_WEIGHTS / ROCK_WEIGHTS.sum()))]
        else:
            name = WRECK_POOL[int(rng.integers(0, len(WRECK_POOL)))]
        r_own = _feature_radius(name)
        if any(math.hypot(cx - px, cz - pz) < r_own + pr for cx, cz in copies for px, pz, pr in obstacles):
            continue
        rot = float(rng.uniform(0, 65535))
        for cx, cz in copies:
            added.append((name, float(cx), float(cz), rot))
            obstacles.append((cx, cz, r_own))
        count += 1
    if not added:
        return
    d.features = list(d.features) + added
    if kind == "trees":
        return
    if kind == "rocks" and "features/forge_rocks.lua" not in d.extra_files:
        # the rock models are written into the archive only for maps with rocks; the same files as decor.place
        from .models import feature_pack
        files, _ = feature_pack("", d.biome, np.random.default_rng(int(d.seed) + 778), crystals=False)
        d.extra_files.update(files)
    _block_trees(d, [(f[1], f[2], _feature_radius(f[0])) for f in added])


def _block_trees(d, pts):
    """No trees grow through new rocks and wrecks (the same cells as decor.place blocks at build time)."""
    nz, nx = d.hm.shape
    tb = np.zeros(d.hm.shape, bool) if d.tree_block is None else d.tree_block.copy()
    for x, z, r in pts:
        i, j = min(nz - 1, max(0, int(z / SQ))), min(nx - 1, max(0, int(x / SQ)))
        rc = int(r / SQ) + 2
        tb[max(0, i - rc):i + rc + 1, max(0, j - rc):j + rc + 1] = True
    d.tree_block = tb


def _set_box(d, sym, e, on, fail):
    """Replace one polygon of a team's start box. With symmetry on, the same polygon is mirrored (rotated) onto the
    team whose start point is the image of this team's start point, so each team keeps its own box."""
    from .app.luatable import startboxes
    from .formats import startboxes_lua, startboxes_to_lua

    team, pi = e.get("team"), e.get("poly")
    if any(not isinstance(v, int) or isinstance(v, bool) for v in (team, pi)):
        raise ValueError("team and poly: integers expected")
    pts = e.get("points")
    if not isinstance(pts, list) or len(pts) < 3:
        raise ValueError("points: at least 3 [x, z] points")
    poly = [_pt(p, "points") for p in pts]

    boxes = startboxes(d.startboxes if d.startboxes is not None else startboxes_lua(sym, d.starts))
    by_team = {b["team"]: b for b in boxes}
    if team not in by_team or not 0 <= pi < len(by_team[team]["polygons"]):
        return fail("start box not found")

    updates = [(team, poly)]
    if on:
        owners = [b for b in boxes if b["startpoints"]]              # teams that have a start point to mirror
        src = by_team[team]["startpoints"]
        if not src:
            return fail("start box not found")
        s = tuple(src[0])
        hits = match_orbit(sym, s, [tuple(b["startpoints"][0]) for b in owners], tol=TOL)
        if hits[0] is None:
            return fail("start box not found")
        for j, h in enumerate(hits):
            if j == 0 or h is None:
                continue
            t = owners[h]["team"]
            if not 0 <= pi < len(by_team[t]["polygons"]):
                return fail("start box not found")
            image = [orbit(sym, p[0], p[1])[j] for p in poly]
            updates.append((t, image))
    for _, q in updates:
        if not all(_inside(sym, p) for p in q):
            return fail("outside the map")

    for t, q in updates:
        by_team[t]["polygons"][pi] = [[float(p[0]), float(p[1])] for p in q]
    d.startboxes = startboxes_to_lua(boxes)
    return None


# ----------------------------------------------------------------------------- live checks
STEEP = 30.0          # degrees: a metal spot or start point on ground steeper than this is flagged
START_MEX_GAP = 120.0  # elmos: a metal spot closer than this to a start point sits inside the commander
BOX_MIN_EDGE = 300.0   # elmos: a start box edge shorter than this is flagged as very small


def _ground(d, x, z):
    """(height, slope) of the heightmap at a spot in elmos."""
    from . import SQ
    h = d.hm
    ix = min(max(int(round(x / SQ)), 0), h.shape[1] - 1)
    iz = min(max(int(round(z / SQ)), 0), h.shape[0] - 1)
    return float(h[iz, ix]), iz, ix


def editor_checks(d, symmetry=True):
    """Checks that only matter once things are moved by hand. -> [{"level": "warn"|"error", "text", "x", "z"}]
    Reachability and the template's own checks come from forge.check()."""
    from .terrain import slope_deg
    slope = slope_deg(d.hm)
    out = []

    def add(level, text, p):
        out.append(dict(level=level, text=text, x=float(p[0]), z=float(p[1])))

    spots = [("Metal spot", (m["x"], m["z"])) for m in d.mexes] + [("Geovent", (g[0], g[1])) for g in d.geos] \
        + [("Start point", (p[0], p[1])) for p in d.starts]
    for what, p in spots:
        h, iz, ix = _ground(d, *p)
        if what != "Start point" or d.movement_profile != "naval":
            if h < 0 and what == "Metal spot":
                pass                                           # underwater metal is allowed on every map (reachability: checks.report)
            elif h < 0 and not (d.blocked is not None and d.blocked[iz, ix]):
                add("error", f"{what} is under water", p)
            elif slope[iz, ix] > STEEP:
                add("warn", f"{what} is on very steep ground", p)
        if what == "Start point" and d.blocked is not None and d.blocked[iz, ix]:
            add("error", "Start point is on ground no unit can stand on", p)
    for m in d.mexes:
        for s in d.starts:
            if math.hypot(m["x"] - s[0], m["z"] - s[1]) < START_MEX_GAP:
                add("warn", "Metal spot is almost on a start point", (m["x"], m["z"]))
                break
    boxes = _start_boxes(d)
    polys = [(b["team"], poly) for b in boxes for poly in b["polygons"]]
    for s in d.starts:
        owner = _box_owner(boxes, s)                           # None: no team has a start point to match
        own = [poly for team, poly in polys if owner is None or team == owner]
        if polys and not any(_in_poly(s, poly) for poly in own):
            add("error", "Start point is outside its start box", s)
    for i, (team, poly) in enumerate(polys):
        if any(not (0 <= x <= d.sym.W and 0 <= z <= d.sym.H) for x, z in poly):
            add("error", "Start box leaves the map", _centre(poly))
        if any(math.hypot(q[0] - p[0], q[1] - p[1]) < BOX_MIN_EDGE for p, q in _edges(poly)):
            add("warn", "Start box is very small", _centre(poly))
        for other_team, other in polys[i + 1:]:
            if other_team != team and _polys_overlap(poly, other):
                add("error", "Start boxes overlap", _centre(poly))
    totals = {}
    for m in d.mexes:
        totals[m["side"]] = totals.get(m["side"], 0.0) + m["metal"]
    if len(totals) > 1 and max(totals.values()) - min(totals.values()) > 0.05:
        label = "player" if isinstance(d.sym, RotSymmetry) else "side"
        add("warn", f"Metal is not equal for every {label} (" + ", ".join(
            f"{k}: {v:.1f}" for k, v in sorted(totals.items())) + ")" + ("" if symmetry else " - symmetry is off"),
            (d.sym.W / 2, d.sym.H / 2))
    return out


def _in_poly(p, poly):
    x, z, inside = p[0], p[1], False
    for (x1, z1), (x2, z2) in zip(poly, poly[1:] + poly[:1]):
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            inside = not inside
    return inside


def _start_boxes(d):
    """Team boxes of the design: its own map_startboxes.lua, or the ones the symmetry layout generates. [] if unreadable."""
    from .app.luatable import startboxes
    from .formats import startboxes_lua
    try:
        return startboxes(d.startboxes if d.startboxes is not None else startboxes_lua(d.sym, d.starts))
    except Exception:
        return []


def _box_owner(boxes, p):
    """Team whose start point is nearest to p (the start point belongs to that team), or None."""
    best = None
    for b in boxes:
        for s in b["startpoints"]:
            dist = math.hypot(s[0] - p[0], s[1] - p[1])
            if best is None or dist < best[0]:
                best = (dist, b["team"])
    return None if best is None else best[1]


def _edges(poly):
    return list(zip(poly, poly[1:] + poly[:1]))


def _centre(poly):
    return (sum(x for x, _ in poly) / len(poly), sum(z for _, z in poly) / len(poly))


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _polys_overlap(p, q):
    """Two polygons share an area or touch edge to edge (proper crossing) or contain a corner of each other."""
    for a, b in _edges(p):
        for c, d in _edges(q):
            if _orient(a, b, c) * _orient(a, b, d) < 0 and _orient(c, d, a) * _orient(c, d, b) < 0:
                return True
    return any(_in_poly(v, q) for v in p) or any(_in_poly(v, p) for v in q)
