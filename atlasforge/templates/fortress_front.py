"""Fortress Front: mirrored forward positions with open sorties and outer expansions."""
import numpy as np

from ..noise import smoothstep
from .base import Param, Template
from ._wildlands import build, common_params, described


def terrain(v, rng, fields):
    _, _, x, z, macro, detail = fields
    # Build two low defensive shoulders around the mirrored home positions.
    starts = ((0.11, 0.5), (0.89, 0.5)) if v["layout"] == "ew" else (
        ((0.5, 0.11), (0.5, 0.89)) if v["layout"] == "ns" else ((0.14, 0.14), (0.86, 0.86)))
    relief = v["fortification"]
    base = 72 + 20 * macro + 5 * detail
    fort = np.zeros_like(x)
    for sx, sz in starts:
        dx, dz = x - sx, z - sz
        radius = np.sqrt(dx * dx + dz * dz)
        # A broken horseshoe faces the contested center; three low corridors remain open.
        radius_scale = 1.12 if v["form"] == "broad" else 0.88
        ring = np.exp(-((radius - 0.145 * radius_scale) / (0.035 * radius_scale)) ** 2)
        toward = np.arctan2(0.5 - sz, 0.5 - sx)
        angle = np.arctan2(dz, dx)
        delta = np.abs((angle - toward + np.pi) % (2 * np.pi) - np.pi)
        gap_front = np.exp(-((delta / 0.24) ** 2))
        gap_flanks = np.maximum(np.exp(-(((delta - 1.05) / 0.20) ** 2)),
                                np.exp(-(((delta + 1.05) / 0.20) ** 2)))
        ring *= 1 - 0.92 * np.maximum(gap_front, gap_flanks)
        keep = 1 - smoothstep(0.20, 0.27, radius)
        fort = np.maximum(fort, ring * keep)
    return (base + relief * (80 + 20 * macro) * fort).astype(np.float32)


class FortressFrontTemplate(Template):
    id = "fortress_front"
    title = "Fortress Front"
    modes = ("1v1", "team")
    tags = ("land", "chokes")
    players = "1v1 to 4v4"
    description = ("Mirrored forward positions face a shared battlefield. Each low defensive shoulder has "
                   "several sorties, while paired expansions lie beyond the home perimeter.")
    params = common_params("temperate") + (
        described(Param("form", "Position profile", "choice", "broad", choices=("broad", "compact"),
                        help="Choose broad or compact defensive shoulders"),
                  "Sets the footprint of each defensive shoulder. Broad positions spread the forward terrain and leave more room for lateral sorties; compact positions concentrate the fight near the exits. For example, broad makes the outer expansion route more exposed."),
        described(Param("fortification", "Fortification relief", "float", 1.0, min=0.6, max=1.5,
                        step=0.1, adv_min=0.2, adv_max=2.4,
                        help="Scales the low ridges around each forward position"),
                  "Sets the height of the broken defensive shoulders around both home positions. Higher ridges make the sorties more important; lower ridges keep the front open. For example, 1.0 gives cover without sealing the home area."),
    )

    def make(self, v, seed, log=print):
        d = build(self, v, seed, terrain, log)
        n = d.hm.shape[0]
        z, x = np.mgrid[:n, :n].astype(np.float32) / (n - 1)
        world_size = v["size"] * 512
        centers = [(sx / world_size, sz / world_size) for sx, sz in d.starts]
        gates = []
        for i, (sx, sz) in enumerate(centers):
            dx, dz = x - sx, z - sz
            radius = np.sqrt(dx * dx + dz * dz)
            toward = np.arctan2(0.5 - sz, 0.5 - sx)
            angle = np.arctan2(dz, dx)
            delta = (angle - toward + np.pi) % (2 * np.pi) - np.pi
            for name, direction in (("center", 0.0), ("north flank", 1.05), ("south flank", -1.05)):
                spread = np.abs((delta - direction + np.pi) % (2 * np.pi) - np.pi)
                mask = (radius > 0.09) & (radius < 0.23) & (spread < 0.20)
                gates.append((f"position {i + 1} {name} sortie", mask))
        clear = np.zeros((n, n), dtype=bool)
        for _, mask in gates:
            clear |= mask
        d.gates = gates
        d.tree_block |= clear
        d.keep_clear |= clear
        d.notes.append("Two mirrored forward positions have a central sortie and two flank exits each.")
        return d
