"""Crater Basin: a traversable outer circuit surrounds a contested basin."""
import numpy as np

from ..noise import smoothstep
from .base import Param, Template
from ._wildlands import build, common_params, described


def terrain(v, rng, fields):
    _, _, x, z, macro, detail = fields
    dx, dz = x - 0.5, z - 0.5
    # x/z are normalized coordinates; the design radii are in elmos.
    # A size-N map spans N * 512 elmos on each axis.
    radius = np.sqrt(dx * dx + dz * dz) * v["size"] * 512
    # A symmetric, continuous ring and lowered basin give a readable crater
    # profile. Four broad radial saddles make crossings reliable at safe bounds.
    ring = smoothstep(v["rim_radius"] - 0.055, v["rim_radius"] - 0.015, radius) * (
        1 - smoothstep(v["rim_radius"] + 0.015, v["rim_radius"] + 0.060, radius))
    basin = 1 - smoothstep(v["basin_radius"] - 0.035, v["basin_radius"] + 0.035, radius)
    angle = np.arctan2(dz, dx)
    ramp = np.zeros_like(radius)
    for a in (0, np.pi / 2, np.pi, 3 * np.pi / 2):
        delta = np.abs(angle - a)
        delta = np.minimum(delta, 2 * np.pi - delta)
        ramp = np.maximum(ramp, np.exp(-((delta / (v["ramp_width"] / (2 * v["rim_radius"]))) ** 2)))
    rim_height = v["relief"] * (108 + 18 * macro)
    base = 78 + 20 * macro + 4 * detail
    crater = rim_height * ring * (1 - 0.90 * ramp) - v["relief"] * (48 + 8 * macro) * basin
    # The far flank remains gently elevated; the ring itself stays broad and
    # low enough for the guaranteed outer rotation route.
    outer_radius = 0.405 * v["size"] * 512
    outer_width = 0.07 * v["size"] * 512
    outer = v["relief"] * 20 * np.exp(-((radius - outer_radius) / outer_width) ** 2)
    return (base + crater + outer).astype(np.float32)


class CraterBasinTemplate(Template):
    id = "crater_basin"
    title = "Crater Basin"
    modes = ("1v1", "team")
    tags = ("land", "chokes")
    players = "1v1 to 4v4"
    description = ("A contested crater basin sits inside a broad, traversable rim. Four marked ramps connect the basin "
                   "to the rim, while a lower outer circuit supports flanking and mirrored resource expansion.")
    params = common_params("temperate") + (
        described(Param("form", "Crater profile", "choice", "classic", choices=("classic", "shallow"),
                        help="Choose a pronounced or shallower crater profile"),
                  "Sets the crater's vertical profile. Classic creates a distinct raised rim and low basin; shallow softens both while keeping their routes. For example, shallow makes the basin easier to enter."),
        described(Param("rim_radius", "Rim radius", "int", 1900, min=1600, max=2200, step=100,
                        adv_min=1400, adv_max=2500, help="Radius of the crater rim in elmos"),
                  "Sets how far the crater rim sits from the center. A larger radius leaves more room inside the basin and on the outer flank. For example, 1900 keeps both routes distinct on a size 12 map."),
        described(Param("basin_radius", "Basin radius", "int", 1050, min=800, max=1300, step=100,
                        adv_min=600, adv_max=1500, help="Radius of the low central basin in elmos"),
                  "Sets the size of the contested low ground. A larger basin gives armies more room after descending the rim. For example, 1050 leaves a central fight area between the four ramps."),
        described(Param("ramp_width", "Ramp width", "int", 340, min=260, max=420, step=20,
                        adv_min=180, adv_max=600, help="Width of the four approaches through the rim"),
                  "Sets the width of four evenly spaced routes between rim and basin. Wider ramps support tanks; narrower ramps concentrate fights. For example, 340 gives broad approaches with clear high ground between them."),
    )

    def make(self, v, seed, log=print):
        # The shallow profile retains the same route topology and economy.
        v = dict(v)
        # Keep the authored proportions on small and large maps alike; otherwise
        # the fixed-elmo rim collides with edge starts at the smallest safe sizes.
        map_scale = v["size"] / 12
        v["rim_radius"] *= map_scale
        v["basin_radius"] *= map_scale
        if v["form"] == "shallow":
            v["relief"] = v["relief"] * 0.62
        d = build(self, v, seed, terrain, log)
        n = d.hm.shape[0]
        z, x = np.mgrid[:n, :n].astype(np.float32) / (n - 1)
        radius = np.sqrt((x - 0.5) ** 2 + (z - 0.5) ** 2)
        angle = np.arctan2(z - 0.5, x - 0.5)
        d.gates = [("outer rim circuit", (radius > 0.34) & (radius < 0.46))]
        for i, direction in enumerate((0, np.pi / 2, np.pi, 3 * np.pi / 2)):
            delta = np.abs(angle - direction)
            delta = np.minimum(delta, 2 * np.pi - delta)
            d.gates.append((f"basin ramp {i + 1}", (radius > 0.11) & (radius < 0.39) & (delta < 0.22)))
        return d
