"""Edit list: "enabled": false keeps an edit in the list and the project file but does not apply it."""
import pytest

from atlasforge import forge
from atlasforge.edits import apply_edits
from atlasforge.project import validate_edits


@pytest.fixture(scope="module")
def design():
    return forge.make("chokepoint", {"size": 12, "gates": 2}, 3)


def _edit(design):
    m = design.mexes[0]
    return {"op": "del_mex", "at": [m["x"], m["z"]]}


def test_disabled_edit_is_not_applied(design):
    e = _edit(design)
    on, _ = apply_edits(design, [e])
    off, problems = apply_edits(design, [dict(e, enabled=False)])
    assert len(on.mexes) < len(design.mexes)
    assert len(off.mexes) == len(design.mexes) and problems == []
    again, _ = apply_edits(design, [dict(e, enabled=True)])
    assert len(again.mexes) == len(on.mexes)


def test_disabled_edit_does_not_block_later_ones(design):
    e = _edit(design)
    d, problems = apply_edits(design, [dict(e, enabled=False), dict(e)])
    assert problems == [] and len(d.mexes) < len(design.mexes)


def test_project_validates_enabled_flag():
    ok = {"op": "del_mex", "at": [1, 2], "enabled": False}
    assert validate_edits([ok]) == [ok]
    with pytest.raises(ValueError, match="enabled"):
        validate_edits([dict(ok, enabled="no")])
