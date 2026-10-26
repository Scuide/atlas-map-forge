"""Contract tests for the Fortress Front layout."""
import json

import numpy as np
import pytest

from atlasforge import templates
from tools.template_workflow import load_template, validate_design

TID = "fortress_front"


@pytest.fixture()
def template(monkeypatch):
    t = load_template(TID)
    monkeypatch.setitem(templates._REGISTRY, TID, t)
    return t


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("layout", ["diag", "ew", "ns"])
def test_mirrored_positions_and_sorties_are_declared(template, seed, layout):
    from atlasforge import forge
    d = forge.make(TID, {"erosion": 0, "layout": layout}, seed=seed, log=lambda *a: None)
    validate_design(d, "competitive")
    ok, lines = forge.check(d)
    assert ok, "\n".join(lines)
    assert len(d.starts) == 2
    assert len(d.gates) == 6
    assert all(np.any(mask) for _, mask in d.gates)
    assert any("two mirrored forward positions" in note.lower() for note in d.notes)


def test_repeatable_and_seed_sensitive(template):
    from atlasforge import forge
    a = forge.make(TID, {"erosion": 0}, seed=1, log=lambda *a: None)
    b = forge.make(TID, {"erosion": 0}, seed=1, log=lambda *a: None)
    c = forge.make(TID, {"erosion": 0}, seed=2, log=lambda *a: None)
    assert np.array_equal(a.hm, b.hm)
    assert not np.array_equal(a.hm, c.hm)


def test_info_and_preview(template):
    from atlasforge import forge
    json.dumps(template.info())
    d = forge.make(TID, {"erosion": 0}, seed=1, log=lambda *a: None)
    assert forge.preview(d, size=256).size == (256, 256)
