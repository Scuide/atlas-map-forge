"""Island Continents: broad opposing continents separated by a fleet channel."""
import numpy as np

from ..terrain import ellipse_sdf
from .base import Param, Template
from ._naval import finish, islands, naval_params, sea


class IslandContinentsTemplate(Template):
    id = "island_continents"
    title = "Island Continents"
    modes = ("1v1", "team")
    tags = ("sea", "landings")
    players = "1v1 to 3v3"
    description = ("Two broad continents give each side room for a substantial land front. "
                   "A deep channel separates them, so fleets carry units to exposed shores "
                   "and create new landing fronts.")
    infos = {
        "continent_width": "Width of each continent as a share of map width. Wider continents give longer inland fronts and reduce the fleet channel.",
        "continent_depth": "North-south depth of each continent as a share of map width. Deeper continents offer more room for land battles and side landings.",
    }
    params = naval_params() + (
        Param("continent_width", "Continent width", "float", 0.26, min=0.24, max=0.28, step=0.02,
              adv_min=0.22, adv_max=0.30, help="East-west width of each continent"),
        Param("continent_depth", "Continent depth", "float", 0.82, min=0.74, max=0.90, step=0.04,
              adv_min=0.62, adv_max=0.96, help="North-south depth of both continents"),
    )

    def make(self, v, seed, log=print):
        h, xx, zz, edge, rng, W = sea(v, seed)
        rx = 0.5 * v["continent_width"] * W
        rz = 0.5 * v["continent_depth"] * W
        cx, cz = 0.25 * W, 0.5 * W

        def shapes():
            yield ellipse_sdf(xx, zz, cx, cz, rx, rz)

        # islands() mirrors the west continent exactly, keeping opposing land and
        # coastal geometries balanced while leaving one broad, navigable channel.
        islands(h, edge, v, shapes())
        base = (cx, cz)
        # The beach flank needs hundreds of elmos to descend from +100 to
        # ship depth. Keep the ports in the central deep channel.
        port = (0.48 * W, cz)
        channel = np.abs(xx - 0.5 * W) < 0.055 * W
        return finish(self, v, h, xx, zz, W, rng, base, port,
                      [("Continental channel", channel)])
