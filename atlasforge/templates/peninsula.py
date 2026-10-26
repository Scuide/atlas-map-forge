"""Peninsula: paired long land tongues create exposed shores and landing flanks."""
import numpy as np

from ..terrain import ellipse_sdf
from .base import Param, Template
from ._naval import finish, islands, naval_params, sea


class Peninsula(Template):
    id = "peninsula"
    title = "Peninsula"
    modes = ("1v1", "team")
    tags = ("sea", "chokes", "landings")
    players = "1v1 to 3v3"
    description = ("Opposing peninsulas project into open water, with defensible necks, "
                   "long exposed coasts and broad side-landing opportunities.")
    infos = {
        "reach": "How far each peninsula projects toward the opposing shore, as a share of map width. Longer reaches create more forward ground and expose more coastline.",
        "neck_width": "Width of the land connection behind each peninsula head, as a share of map width. A narrow neck is easier to hold and easier to bypass by sea.",
        "head_width": "Width of the broad forward landing area, as a share of map width.",
    }
    params = naval_params() + (
        Param("reach", "Peninsula reach", "float", 0.32, min=0.26, max=0.38, step=0.02,
              adv_min=0.20, adv_max=0.44, help="Projection from the home coast toward the map centre"),
        Param("neck_width", "Neck width", "float", 0.13, min=0.10, max=0.16, step=0.02,
              adv_min=0.07, adv_max=0.20, help="Land width at the peninsula neck"),
        Param("head_width", "Head width", "float", 0.22, min=0.18, max=0.28, step=0.02,
              adv_min=0.14, adv_max=0.34, help="Width of the expanded forward landing ground"),
    )

    def make(self, v, seed, log=print):
        h, xx, zz, edge, rng, W = sea(v, seed)
        reach = v["reach"] * W
        neck = v["neck_width"] * W / 2
        head = v["head_width"] * W / 2
        # Build a west landmass, a narrowing connector, and an expanded outer head.
        # The east side is reflected by islands(), retaining exact EW symmetry.
        start_x = 0.105 * W
        neck_end = min(0.5 * W - 0.13 * W, start_x + reach * 0.68)
        head_radius = max(0.09 * W, reach * 0.30)
        head_x = min(0.5 * W - head_radius - 0.06 * W, start_x + reach)
        z0 = 0.5 * W

        def capsule(x1, x2, z, radius):
            dx = x2 - x1
            t = np.clip(((xx - x1) * dx + (zz - z) * 0) / (dx * dx + 1e-9), 0, 1)
            return np.hypot(xx - (x1 + t * dx), zz - z) - radius

        def shapes():
            yield ellipse_sdf(xx, zz, start_x, z0, 0.22 * W, 0.31 * W)
            yield capsule(start_x, neck_end, z0, neck)
            yield ellipse_sdf(xx, zz, head_x, z0, head_radius, head)

        islands(h, edge, v, shapes())
        base = (0.105 * W, z0)
        port = (0.105 * W, z0 + 0.40 * W)
        gates = [("peninsula neck", (np.abs(xx - (start_x + neck_end) / 2) < 0.07 * W) &
                  (np.abs(zz - z0) < 0.5 * W))]
        return finish(self, v, h, xx, zz, W, rng, base, port, gates)
