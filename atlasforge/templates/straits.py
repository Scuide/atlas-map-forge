"""Island Straits: long central islands split the water into named fleet passages."""
import numpy as np

from ..terrain import box_sdf, plateau
from .base import Param, Template
from ._naval import finish, island, naval_params, sea


class IslandStraits(Template):
    id = "straits"
    title = "Island Straits"
    modes = ("1v1", "team")
    tags = ("sea", "chokes")
    players = "1v1 to 3v3"
    description = ("Long central islands split the sea into fleet passages between opposing coastal bases. "
                   "Fight for the straits and use amphibious landings to capture the central islands.")
    infos = {
        "depth": "Depth of the open sea in elmos below the water surface. Ships need more than 15 elmos; submarines are hidden better in deep water. Shallow seas (100) let amphibians walk across quickly; deep seas (300) keep the ocean a ship's world.",
        "beach_slope": "Steepness of the beaches in degrees between the seabed and the dry land. Tanks and hovers can drive up to about 27 degrees, so gentle beaches (10) make landings easy; steep ones (18) slow down amphibious attacks.",
        "coast_noise": "How irregular the coastlines are, in elmos. 0 gives smooth round islands; 100 gives bays and capes that offer cover and landing spots.",
        "sea_metal": "Share of the expansion metal spots that lie on the seabed instead of on land. Underwater spots can be taken by amphibious builders and ships' constructors and are defended with ships and torpedo turrets. 0.3 keeps most metal on land, 0.8 makes the sea the main economy.",
        "geovents": "Adds one geothermal vent on each home island. The general 'Geothermal vents' setting overrides this when it is not set to 'template'.",
        "coast_size": "Size of the dry coastal base area. Larger coasts give more room to build; smaller ones push players to expand onto the seabed early.",
        "island_pairs": "Number of mirrored islands in the sea. Islands give safe land for expansions and break up the open water into routes for ships.",
        "island_size": "Size of the expansion islands. Larger islands narrow the sea lanes between them, which makes fleet battles more cramped.",
        "scatter": "How far the expansion islands are moved away from a regular grid (set by the seed). 0 gives a tidy, predictable layout; 1 a natural, irregular one. The map stays mirrored either way.",
        "passages": "Number of water passages between the central islands and the map edges. Each passage is a fleet route; fewer passages give heavier naval fights.",
        "passage_width": "Width of each water passage at the waterline, in elmos. Narrow passages are easy to block with ships and coastal defences; wide ones let fleets manoeuvre.",
        "island_width": "East-west width of the central islands in elmos. Wide islands are valuable ground for amphibious landings and long-range defences.",
    }
    params = naval_params() + (
        Param("passages", "Fleet passages", "int", 3, min=2, max=4, step=1,
              adv_min=1, adv_max=7, help="Number of east-west gaps between the central islands and map edges"),
        Param("passage_width", "Passage width", "int", 1100, min=800, max=1500, step=50,
              adv_min=300, adv_max=3000, help="Approximate waterline width in elmos at the default map size"),
        Param("island_width", "Central island width", "int", 1500, min=1000, max=1800, step=100,
              adv_min=400, adv_max=3000, help="East-west width of the central islands in elmos"),
    )

    def make(self, v, seed, log=print):
        h, xx, zz, edge, rng, W = sea(v, seed)
        island(h, xx, zz, edge, v, 0.025 * W, 0.5 * W, 0.15 * W, 0.34 * W)
        count = v["passages"]
        scale = W / 8192
        gap = v["passage_width"] * scale
        # Subtract the beach run so the parameter describes water rather than plateau tops.
        shore = 100 / np.tan(np.radians(v["beach_slope"]))
        radius_z = max(24.0, (W / count - gap) / 2 - shore)
        for k in range(count - 1):
            radius_x = v["island_width"] * scale / 2
            radius = min(radius_x, radius_z)
            # Exact capsule distance keeps beach runs predictable even for very thin islands.
            # The ellipse approximation otherwise expands diagonal shoulders into adjacent straits.
            sdf = box_sdf(xx, zz, W / 2, (k + 1) * W / count,
                          radius_x - radius, radius_z - radius) - radius
            plateau(h, sdf, 100, side_deg=v["beach_slope"], noise=edge, amp=v["coast_noise"])
        zs = [(k + 0.5) * W / count for k in range(count)]
        gates = [(f"strait {k + 1}", (np.abs(xx - W / 2) < 120 * scale) &
                  (np.abs(zz - z) < W / (2 * count))) for k, z in enumerate(zs)]
        return finish(self, v, h, xx, zz, W, rng, (0.085 * W, 0.5 * W),
                      (0.30 * W, W * (0.5 + (0.5 / count if count % 2 == 0 else 0))), gates)
