"""Live editor checks after manual edits (SCU-35): atlasforge.edits.editor_checks on edited designs."""
import math

import numpy as np
import pytest

from atlasforge import SQ, forge
from atlasforge.edits import START_MEX_GAP, apply_edits, editor_checks

QUIET = dict(log=lambda *a, **k: None)
FAST = {"erosion": 0, "rocks": 0, "wrecks": 0}


@pytest.fixture(scope="module")
def skirmish():
    return forge.make("skirmish", dict(FAST), seed=1, **QUIET)


@pytest.fixture(scope="module")
def ocean():
    return forge.make("open_sea", dict(FAST, size=12), seed=1, **QUIET)


def _deep_water(d):
    """First deep-water cell at least 150 elmos from every metal spot, geovent and start (deterministic scan)."""
    pts = [(m["x"], m["z"]) for m in d.mexes] + list(d.geos) + list(d.starts)
    for iz, ix in np.argwhere(d.hm < -30):
        x, z = float(ix * SQ), float(iz * SQ)
        if all(math.hypot(x - p[0], z - p[1]) > 150 for p in pts):
            return x, z
    raise AssertionError("no deep-water cell far enough from the objects")


def test_untouched_standard_design_has_no_errors(skirmish):
    errors = [i for i in editor_checks(skirmish) if i["level"] == "error"]
    assert not errors


def test_mex_moved_under_water_is_an_error(ocean):
    m = ocean.mexes[0]
    to = _deep_water(ocean)
    d, problems = apply_edits(
        ocean, [{"op": "move_mex", "from": [m["x"], m["z"]], "to": list(to)}], symmetry=False)
    assert not problems
    errs = [i for i in editor_checks(d) if i["level"] == "error" and "under water" in i["text"]]
    assert any(math.hypot(i["x"] - to[0], i["z"] - to[1]) < 1e-6 for i in errs), errs


def test_start_point_next_to_a_mex_warns(skirmish):
    d = skirmish
    W, H = d.sym.W, d.sym.H
    s0 = d.starts[0]
    far = [m for m in d.mexes if math.hypot(m["x"] - s0[0], m["z"] - s0[1]) > START_MEX_GAP + 60]
    assert far, "expected a metal spot away from the first start point"
    m = min(far, key=lambda q: abs(q["x"] - W / 2) + abs(q["z"] - H / 2))
    t = (m["x"] + (60.0 if m["x"] + 60 <= W else -60.0), m["z"])
    d, problems = apply_edits(
        d, [{"op": "move_start", "from": list(s0), "to": [t[0], t[1]]}], symmetry=False)
    assert not problems
    warns = [i for i in editor_checks(d) if i["level"] == "warn" and "almost on a start point" in i["text"]]
    assert warns


def test_unequal_metal_per_side_warns(skirmish):
    m = skirmish.mexes[0]
    before = [i for i in editor_checks(skirmish) if i["text"].startswith("Metal is not equal")]
    assert not before, "template design should start out balanced"
    d, problems = apply_edits(
        skirmish, [{"op": "set_metal", "at": [m["x"], m["z"]], "metal": m["metal"] + 2.0}], symmetry=False)
    assert not problems
    warns = [i for i in editor_checks(d, symmetry=False) if i["level"] == "warn"
             and i["text"].startswith("Metal is not equal")]
    assert warns, "expected an unequal-metal warning after raising one spot by 2.0"
    assert all("symmetry is off" in w["text"] for w in warns)


def test_every_entry_has_level_text_x_z(skirmish, ocean):
    entries = list(editor_checks(ocean))
    m = skirmish.mexes[0]
    d, _ = apply_edits(
        skirmish, [{"op": "set_metal", "at": [m["x"], m["z"]], "metal": m["metal"] + 2.0}], symmetry=False)
    entries += editor_checks(d, symmetry=False)
    assert entries, "expected at least one check entry to inspect"
    for i in entries:
        assert {"level", "text", "x", "z"} <= set(i)


def test_start_point_in_water_is_an_error(skirmish):
    from atlasforge.edits import copy_design
    d = copy_design(skirmish)
    d.hm = d.hm.copy()
    sx, sz = d.starts[0][0], d.starts[0][1]
    d.hm[int(round(sz / SQ)), int(round(sx / SQ))] = -50.0
    errs = [i for i in editor_checks(d) if i["level"] == "error" and i["text"] == "Start point is under water"]
    assert any(math.hypot(i["x"] - sx, i["z"] - sz) < 1e-6 for i in errs), errs
