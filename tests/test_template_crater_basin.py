"""Focused contract tests for Crater Basin."""
import json
import numpy as np
import pytest

from atlasforge import templates
from tools.template_workflow import load_template, validate_design

TID = "crater_basin"


@pytest.fixture()
def template(monkeypatch):
    t = load_template(TID)
    monkeypatch.setitem(templates._REGISTRY, TID, t)
    return t


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_default_design_is_playable(template, seed):
    from atlasforge import forge
    d = forge.make(TID, {"erosion": 0}, seed=seed, log=lambda *a: None)
    validate_design(d, "competitive")
    ok, lines = forge.check(d)
    assert ok, "\n".join(lines)
    assert len(d.gates) == 5
    assert any("outer rim" in name for name, _ in d.gates)


def test_seed_changes_terrain_and_repeats_deterministically(template):
    from atlasforge import forge
    a = forge.make(TID, {"erosion": 0}, seed=1, log=lambda *a: None)
    b = forge.make(TID, {"erosion": 0}, seed=1, log=lambda *a: None)
    c = forge.make(TID, {"erosion": 0}, seed=2, log=lambda *a: None)
    assert np.array_equal(a.hm, b.hm)
    assert not np.array_equal(a.hm, c.hm)


def test_parameter_info_and_preview(template):
    from atlasforge import forge
    json.dumps(template.info())
    d = forge.make(TID, {"erosion": 0}, seed=1, log=lambda *a: None)
    assert forge.preview(d, size=256).size == (256, 256)


def test_advanced_extremes_do_not_crash(template):
    from atlasforge import forge
    for key, values in (("rim_radius", (1400, 2500)), ("basin_radius", (600, 1500)),
                        ("ramp_width", (180, 600)), ("form", ("classic", "shallow"))):
        for value in values:
            forge.make(TID, {key: value, "erosion": 0}, seed=1, log=lambda *a: None, advanced=True)


def test_terrain_has_basin_rim_and_four_radial_ramps():
    from atlasforge.templates.crater_basin import terrain

    values = {"size": 12, "rim_radius": 1900, "basin_radius": 1050,
              "ramp_width": 340, "relief": 1.0}

    def sample(radius_elmos, angle):
        radius = radius_elmos / (values["size"] * 512)
        x = np.array([[0.5 + radius * np.cos(angle)]], dtype=np.float32)
        z = np.array([[0.5 + radius * np.sin(angle)]], dtype=np.float32)
        zero = np.zeros_like(x)
        return float(terrain(values, None, (x, z, x, z, zero, zero))[0, 0])

    center = sample(0, 0)
    rim_between_ramps = sample(1900, np.pi / 4)
    outside = sample(2700, np.pi / 4)
    assert center < rim_between_ramps
    assert rim_between_ramps > outside
    for angle in (0, np.pi / 2, np.pi, 3 * np.pi / 2):
        assert sample(1900, angle) < rim_between_ramps
