"""Procedural Skirmish: noise terrain in five styles, symmetric resources, ramps carved for tanks."""
from .. import procedural
from .base import Param, Template
from .common import biome_param, size_param


class Skirmish(Template):
    id = "skirmish"
    title = "Procedural Skirmish"
    description = ("Classic 1v1 or team map from noise terrain: hills, plateaus, canyons, islands or craters. "
                   "Ramps are carved automatically so tanks reach every base and metal spot.")
    params = (
        size_param((8, 10, 12, 14, 16, 18, 20), 12),
        biome_param("temperate"),
        Param("style", "Terrain style", "choice", "hills", choices=procedural.STYLES,
              help="hills: rolling hills and mountains; plateaus: terraces with cliffs; canyon: river valleys; "
                   "islands: land in water (hovers and amphibians shine); crater: impact craters"),
        Param("layout", "Teams face", "choice", "diag", choices=procedural.LAYOUTS,
              help="diag: north-west vs south-east; ns: north vs south; ew: west vs east"),
        Param("relief", "Relief", "float", 1.0, min=0.5, max=1.6, step=0.1, adv_min=0.1, adv_max=3.0, help="Height scale, 1.0 = default"),
        Param("mexes", "Metal spots per side", "int", 0, min=0, max=40, step=1, adv_max=100, help="0 = automatic"),
    )

    def make(self, v, seed, log=print):
        s = v["size"]
        return procedural.design((s, s), seed, v["biome"], v["style"], v["layout"], v["relief"],
                                 v["mexes"] or None, log)
