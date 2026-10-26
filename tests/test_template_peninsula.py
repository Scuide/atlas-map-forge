"""Geometry, routes and metadata checks for the Peninsula naval template."""
import json

import numpy as np
from scipy import ndimage

from atlasforge import forge
from atlasforge.checks import connected
from atlasforge.templates import get

TID = "peninsula"
QUIET = lambda *a: None


def test_default_design_and_metadata():
    d = forge.make(TID, seed=1, log=QUIET)
    ok, lines = forge.check(d)
    assert ok, "\n".join(lines)
    assert d.movement_profile == "naval"
    assert len(d.teams) == 2 and d.mexes
    assert "peninsulas" in get(TID).description.lower()
    json.dumps(get(TID).info())


def test_home_land_and_naval_crossing_are_connected():
    d = forge.make(TID, {"erosion": 0}, seed=2, log=QUIET)
    land = ndimage.binary_erosion(d.hm > 30, iterations=3)
    water = ndimage.binary_erosion(d.hm < -35, iterations=4)
    # Peninsulas are separated by sea; each start must sit on its own solid landmass.
    assert all(connected(land, s, s) for s in d.starts)
    assert connected(water, d.naval_starts[0][0], d.naval_starts[1][0])


def test_symmetry_and_determinism():
    a = forge.make(TID, {"erosion": 0}, seed=4, log=QUIET)
    b = forge.make(TID, {"erosion": 0}, seed=4, log=QUIET)
    assert np.array_equal(a.hm, b.hm)
    assert np.array_equal(a.hm, a.hm[:, ::-1])
    assert a.starts == b.starts and a.mexes == b.mexes


def test_geometry_parameters_are_inspectable():
    for key in ("reach", "neck_width", "head_width"):
        for value in get(TID).param(key).limits():
            d = forge.make(TID, {key: value, "erosion": 0}, seed=1, log=QUIET)
            assert np.isfinite(d.hm).all()
            forge.check(d)
            assert forge.preview(d, size=128).size == (128, 128)
