"""Geometry and independent land/naval route checks for Island Continents."""
import json

import numpy as np
import pytest
from scipy import ndimage

from atlasforge import templates
from atlasforge.checks import connected
from atlasforge import forge
from tools.template_workflow import load_template

TID = "island_continents"
QUIET = lambda *a: None


@pytest.fixture()
def template(monkeypatch):
    t = load_template(TID)
    monkeypatch.setitem(templates._REGISTRY, TID, t)
    return t


def test_default_design_and_player_text(template):
    d = forge.make(TID, seed=1, log=QUIET)
    ok, lines = forge.check(d)
    assert ok, "\n".join(lines)
    assert d.movement_profile == "naval"
    assert len(d.teams) == 2 and d.mexes
    assert d.naval_starts[1][0][0] - d.naval_starts[0][0][0] > 300
    assert "two broad continents" in template.description.lower()
    json.dumps(template.info())


@pytest.mark.parametrize("values", [{"size": 12}, {"beach_slope": 10}])
def test_ports_remain_deep_with_small_maps_and_gentle_beaches(template, values):
    d = forge.make(TID, {**values, "erosion": 0}, seed=1, log=QUIET)
    ok, lines = forge.check(d)
    assert ok, "\n".join(lines)


def test_each_continent_has_a_connected_land_front(template):
    d = forge.make(TID, {"erosion": 0}, seed=2, log=QUIET)
    land = ndimage.binary_erosion(d.hm > 30, iterations=3)
    labels, _ = ndimage.label(land)
    a, b = d.starts
    west = labels[int(a[1] / 8), int(a[0] / 8)]
    east = labels[int(b[1] / 8), int(b[0] / 8)]
    assert west != 0 and east != 0 and west != east
    assert np.count_nonzero(labels == west) > 20_000
    assert np.count_nonzero(labels == east) > 20_000


def test_channel_is_a_connected_ship_route(template):
    d = forge.make(TID, {"erosion": 0}, seed=2, log=QUIET)
    sea = ndimage.binary_erosion(d.hm < -35, iterations=4)
    assert connected(sea, d.naval_starts[0][0], d.naval_starts[1][0])


def test_symmetry_and_determinism(template):
    a = forge.make(TID, {"erosion": 0}, seed=4, log=QUIET)
    b = forge.make(TID, {"erosion": 0}, seed=4, log=QUIET)
    assert np.array_equal(a.hm, b.hm)
    assert np.array_equal(a.hm, a.hm[:, ::-1])
    assert a.starts == b.starts and a.mexes == b.mexes
