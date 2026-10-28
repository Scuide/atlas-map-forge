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
    {"op": "features", "kind": "trees", "mode": "add"|"remove", "at": [x, z], "radius": r, "density": d}
     (trees in a disc: remove takes out the random and added trees in it, add plants trees on dry, flat ground)

Objects are found by position (nearest within TOL elmos), not by index, so edits stay meaningful after the
settings change. With symmetry on, an edit acts on the whole orbit of the clicked object (mirror image, or the
N rotations of a free-for-all map). Edits that cannot be applied are returned as problems, never raised.
"""
import dataclasses
import math

import numpy as np

from . import SQ
from .symmetry import RotSymmetry, match_orbit, orbit, orbit_degenerate
from .terrain import slope_deg

TOL = 24.0            # elmos: how far from an object a click may be to address it
MIN_GAP = 40.0        # elmos: closest allowed distance between two metal spots / geovents

OPS = ("move_mex", "add_mex", "del_mex", "set_metal", "move_geo", "add_geo", "del_geo", "move_start", "set_box",
       "brush", "features")
BRUSHES = ("raise", "lower", "flatten", "smooth", "ramp")
FEATURE_KINDS = ("trees",)            # rocks: not yet (they need their feature defs in the archive)
FEATURE_MODES = ("add", "remove")
TREE_GAP = 40.0       # elmos: closest allowed distance between two added trees


def copy_design(d):
    """Cheap copy for editing: the heightmap and masks are shared, only the editable lists are copied."""
    return dataclasses.replace(
        d, mexes=[dict(m) for m in d.mexes], geos=[tuple(g) for g in d.geos],
        starts=[tuple(p) for p in d.starts], teams=[[tuple(p) for p in t] for t in d.teams], notes=list(d.notes),
        features=list(d.features))


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
    """Validated (tool, at, radius, strength, amount, target, to) of a brush edit; ValueError when malformed.
    to is the end point B of a ramp (None for the other tools)."""
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
    if target is not None and (tool != "flatten" or not isinstance(target, (int, float)) or isinstance(target, bool)
                               or not math.isfinite(target)):
        raise ValueError("target: a number, for flatten only")
    to = None
    if tool == "ramp":
        to = _pt(e.get("to"), "to")
    elif e.get("to") is not None:
        raise ValueError("to: for ramp only")
    return (tool, at, float(radius), float(strength), float(amount),
            None if target is None else float(target), to)


def _brush(d, sym, e, on, fail):
    """Apply a terrain brush (brushes.py) at a point, mirrored or rotated over its orbit when symmetry is on.
    The height map is replaced by a new array; the edit list itself is the undo history."""
    from . import brushes

    tool, at, radius, strength, amount, target, to = brush_params(e)
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
        else:
            hm = brushes.smooth(hm, cx, cz, radius, strength)
    d.hm = hm
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


def _features(d, sym, e, on, fail):
    """Add or remove trees in a disc. Remove blocks the random trees in the disc (tree_block) and drops the added
    trees there; add places trees at seeded random spots, each with its whole orbit, so the forest stays symmetric."""
    kind, mode, at, radius, density = feature_params(e)
    spots = _targets(sym, at, on)
    if not all(_inside(sym, s) for s in spots):
        return fail("outside the map")
    why = _orbit_ok(sym, at, on)
    if why:
        return fail(why)
    if mode == "remove":
        _remove_trees(d, spots, radius)
    else:
        _add_trees(d, sym, at, radius, density, on)
    return None


def _remove_trees(d, spots, r):
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
                  if not (f[0].startswith("treetype") and any(math.hypot(f[1] - cx, f[2] - cz) <= r for cx, cz in spots))]


def _add_trees(d, sym, at, radius, density, on):
    """Plant about density * one tree per 40x40 elmos in the disc, on ground no steeper than 20 degrees and above
    the water line, away from metal, geovents and start points. The seed comes from the design and the spot."""
    n = int(round(density * math.pi * radius * radius / 1600.0))
    if n <= 0:
        return
    rng = np.random.default_rng([int(d.seed), int(round(at[0])), int(round(at[1])), n])
    hm = d.hm
    nz, nx = hm.shape
    sl = slope_deg(hm)
    blockers = [(m["x"], m["z"], 120) for m in d.mexes] + [(g[0], g[1], 150) for g in d.geos] + \
               [(s[0], s[1], 700) for s in d.starts]
    placed = [(f[1], f[2]) for f in d.features if f[0].startswith("treetype")]
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
        if hm[i, j] < 6 or sl[i, j] > 20:
            continue
        copies = [c for c in _targets(sym, (x, z), on) if _inside(sym, c)]
        if any(math.hypot(cx - bx, cz - bz) < br for cx, cz in copies for bx, bz, br in blockers):
            continue
        if any(math.hypot(cx - px, cz - pz) < TREE_GAP for cx, cz in copies for px, pz in placed):
            continue
        t = int(rng.integers(0, 16))
        rot = float(rng.uniform(0, 65535))
        for cx, cz in copies:
            added.append((f"treetype{t}", float(cx), float(cz), rot))
            placed.append((cx, cz))
        count += 1
    d.features = list(d.features) + added


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
