"""Geometry and independent ground/naval route tests for Inland Sea."""
import json

import numpy as np
from scipy import ndimage

from atlasforge import forge
from atlasforge.checks import connected
from atlasforge.templates import get

TID = "inland_sea"
QUIET = lambda *a: None


def test_default_design_and_player_text():
    d = forge.make(TID, seed=1, log=QUIET)
    ok, lines = forge.check(d)
    assert ok, "\n".join(lines)
    assert d.movement_profile == "naval"
    assert len(d.teams) == 2 and d.mexes
    assert "land rim" in get(TID).description.lower()
    json.dumps(get(TID).info())


def test_land_route_around_lake_is_connected():
    d = forge.make(TID, {"erosion": 0}, seed=2, log=QUIET)
    land = ndimage.binary_erosion(d.hm > 30, iterations=3)
    assert connected(land, *d.starts)
    assert d.hm[int(d.starts[0][1] / 8), int(d.starts[0][0] / 8)] > 65


def test_separate_inland_sea_route_is_connected():
    d = forge.make(TID, {"erosion": 0}, seed=2, log=QUIET)
    sea = ndimage.binary_erosion(d.hm < -35, iterations=4)
    assert connected(sea, d.naval_starts[0][0], d.naval_starts[1][0])
    # The inner lake and outside ocean are separate basins, as intended.
    labels, _ = ndimage.label(d.hm < -15)
    p = d.naval_starts[0][0]
    assert labels[int(p[1] / 8), int(p[0] / 8)] != 0


def test_ring_symmetry_and_determinism():
    a = forge.make(TID, {"erosion": 0}, seed=4, log=QUIET)
    b = forge.make(TID, {"erosion": 0}, seed=4, log=QUIET)
    assert np.array_equal(a.hm, b.hm)
    assert np.array_equal(a.hm, a.hm[:, ::-1])
    assert a.starts == b.starts and a.mexes == b.mexes


def test_parameter_limits_remain_inspectable():
    t = get(TID)
    for key in ("lake_size", "rim_width"):
        for value in t.param(key).limits():
            d = forge.make(TID, {key: value, "erosion": 0}, seed=1, log=QUIET)
            assert np.isfinite(d.hm).all()
            forge.check(d)
            assert forge.preview(d, size=128).size == (128, 128)
