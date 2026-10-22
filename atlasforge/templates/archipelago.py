"""Archipelago: paired home islands and staggered stepping stones separated by sea lanes."""
import numpy as np

from .base import Param, Template
from ._naval import finish, island, naval_params, sea


class Archipelago(Template):
    id = "archipelago"
    title = "Archipelago"
    modes = ("1v1", "team")
    tags = ("sea",)
    players = "1v1 to 3v3"
    description = ("Home islands and scattered expansion islands divide a deep sea into winding fleet routes. "
                   "Capture island economy with amphibians and defend underwater resources with ships.")
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
        Param("island_pairs", "Expansion island pairs", "int", 3, min=1, max=4, step=1,
              adv_min=0, adv_max=8, help="Number of mirrored expansion islands"),
        Param("island_size", "Expansion island size", "float", 1.0, min=0.7, max=1.2, step=0.05,
              adv_min=0.3, adv_max=2.0, help="Scales expansion islands and narrows surrounding sea lanes"),
        Param("scatter", "Island scatter", "float", 0.7, min=0.0, max=1.0, step=0.1,
              adv_max=2.0, help="Seeded displacement of expansion islands inside their allotted regions"),
    )

    def make(self, v, seed, log=print):
        h, xx, zz, edge, rng, W = sea(v, seed)
        island(h, xx, zz, edge, v, 0.115 * W, 0.5 * W, 0.085 * W, 0.18 * W)
        count = v["island_pairs"]
        # Separate rows leave transverse fleet routes between the stepping stones.
        for k in range(count):
            x = W * (0.38 + 0.015 * np.sin(k * 2.4))
            z = W * (0.14 + 0.72 * (k + 0.5) / max(count, 1))
            jitter = rng.uniform(-0.012, 0.012, 2) * W * v["scatter"]
            r = W * 0.036 * v["island_size"]
            island(h, xx, zz, edge, v, x + jitter[0], z + jitter[1], r, r * 1.18)
        return finish(self, v, h, xx, zz, W, rng, (0.115 * W, 0.5 * W), (0.115 * W, 0.20 * W))
