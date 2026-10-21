"""Reachability checks per Zero-K movement class, using the engine's slope test (terrain.move_slope).

Effective limits (movedef maxSlope x 1.5 in the engine): tanks and hovers 27 degrees real slope,
bots and amphibians 54 degrees. Water depth limit for tanks and bots: 22 elmos.
"""
import numpy as np
from scipy import ndimage

from . import SQ
from .terrain import move_slope

CLASSES = ("tanks", "bots", "spiders", "amphibians", "hovers")


def unit_masks(hm):
    """Bool grids: where each movement class can stand and drive."""
    sl = move_slope(hm)
    return {
        "tanks": (sl < 18) & (hm > -22),
        "bots": (sl < 36) & (hm > -16),
        "spiders": hm > -22,
        "amphibians": sl < 36,
        "hovers": (sl < 18) | (hm < 0),
    }


def cell(p):
    return int(p[1] / SQ), int(p[0] / SQ)


def connected(mask, a, b):
    lab, _ = ndimage.label(mask)
    la, lb = lab[cell(a)], lab[cell(b)]
    return bool(la > 0 and la == lb)


def unreachable_mexes(hm, mexes, start, cls="tanks"):
    lab, _ = ndimage.label(unit_masks(hm)[cls])
    a = lab[cell(start)]
    return [m for m in mexes if lab[int(m["z"] / SQ), int(m["x"] / SQ)] != a]


def report(hm, team0, team1, mexes=(), gates=None):
    """Plain-English check report.
    team0/team1: start points per team; gates: optional [(name, bool mask)] of choke areas.
    Returns (ok, lines). ok = tanks and bots reach the enemy and every metal spot is reachable for tanks."""
    lines = []
    ok = True
    masks = unit_masks(hm)
    for cls in CLASSES:
        m = masks[cls]
        reach = connected(m, team0[0], team1[0])
        own = all(connected(m, team0[0], p) for p in team0[1:]) and all(connected(m, team1[0], p) for p in team1[1:])
        text = f"{cls.capitalize():11s} can reach the enemy: {'yes' if reach else 'NO'}"
        if not own:
            text += " (own bases are not connected!)"
        if gates:
            via = []
            for gname, gm in gates:
                others = np.zeros(hm.shape, bool)
                for g2, gm2 in gates:
                    if g2 != gname:
                        others |= gm2
                if connected(m & ~others, team0[0], team1[0]):
                    via.append(gname)
            allg = np.zeros(hm.shape, bool)
            for _, gm in gates:
                allg |= gm
            sealed = not connected(m & ~allg, team0[0], team1[0])
            if reach:
                text += f", only through: {', '.join(via) or '-'}" if sealed else ", also outside the chokes"
        lines.append(text)
        if cls in ("tanks", "bots"):
            ok &= reach and own
    if len(mexes):
        bad = unreachable_mexes(hm, mexes, team0[0])
        lines.append(f"Metal spots unreachable for tanks: {len(bad)} of {len(mexes)}")
        ok &= not bad
    return ok, lines
