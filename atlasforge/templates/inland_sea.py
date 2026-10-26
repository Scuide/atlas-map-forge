"""Inland Sea: a continuous land rim surrounds a navigable central lake."""
import numpy as np

from ..terrain import ellipse_sdf
from .base import Param, Template
from ._naval import finish, islands, naval_params, sea


class InlandSea(Template):
    id = "inland_sea"
    title = "Inland Sea"
    modes = ("1v1", "team")
    tags = ("sea", "chokes")
    players = "1v1 to 3v3"
    description = ("A connected land rim circles a large inland sea. Ground forces take the long route "
                   "around the shore while fleets cross the lake quickly between the opposing ports.")
    infos = {
        "rim_width": "Width of the continuous land rim between the inland sea and the outer water, in elmos. Wider rims create longer ground routes and more room for land battles.",
        "lake_size": "Size of the central inland sea. A larger lake gives fleets more room and makes the land route around it longer.",
    }
    params = naval_params() + (
        Param("lake_size", "Inland sea size", "float", 0.52, min=0.46, max=0.58, step=0.02,
            adv_min=0.40, adv_max=0.64, help="Scale of the central lake relative to the map"),
        Param("rim_width", "Land rim width", "float", 0.16, min=0.12, max=0.20, step=0.02,
            adv_min=0.08, adv_max=0.24, help="Width of the land ring relative to the map"),
    )

    def make(self, v, seed, log=print):
        h, xx, zz, edge, rng, W = sea(v, seed)
        # Build the annulus as a signed-distance field. The inner and outer water
        # bodies remain separate so the inland lake itself is a single safe fleet route.
        inner_r = 0.43 * W * v["lake_size"]
        rim = v["rim_width"] * W
        outer_r = inner_r + rim

        def shapes():
            outer = ellipse_sdf(xx, zz, W / 2, W / 2, outer_r, outer_r)
            inner = ellipse_sdf(xx, zz, W / 2, W / 2, inner_r, inner_r)
            # max(outer, -inner) is negative only on the ring.
            yield np.maximum(outer, -inner)

        islands(h, edge, v, shapes())
        base = (0.5 * W - (outer_r + inner_r) / 2, 0.5 * W)
        port = (0.5 * W - inner_r * 0.35, 0.5 * W)
        gates = [("inland sea", (np.hypot(xx - W / 2, zz - W / 2) < inner_r * 0.94))]
        return finish(self, v, h, xx, zz, W, rng, base, port, gates)
