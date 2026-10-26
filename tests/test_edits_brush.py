"""Brush edits (editor stage B): terrain brushes stored in the edit list, applied to the height map before the build,
mirrored with the symmetry, undone by dropping the entry, and saved in .forge.json without changing old files."""
import numpy as np
import pytest

from atlasforge import forge, project
from atlasforge.edits import apply_edits
from atlasforge.symmetry import orbit

QUIET = dict(log=lambda *a: None)


@pytest.fixture(scope="module")
def arena():
    return forge.make("arena", {"size": 12, "erosion": 0}, seed=2, **QUIET)


def _cell(d, x, z):
    from atlasforge import SQ
    return int(round(z / SQ)), int(round(x / SQ))


def _brush(x, z, tool="raise", **kw):
    e = dict(op="brush", tool=tool, at=[x, z], radius=600.0, strength=1.0)
    e.update(kw)
    return e


def test_brush_edit_changes_height_map_and_keeps_base(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    base = arena.hm.copy()
    d, problems = apply_edits(arena, [_brush(x, z, amount=50.0)], symmetry=False)
    assert problems == []
    iz, ix = _cell(d, x, z)
    assert d.hm[iz, ix] == pytest.approx(base[iz, ix] + 50.0, abs=1.0)   # the cell nearest the centre: w ~ 1
    assert np.array_equal(arena.hm, base)                   # the design the edits are applied to is not modified


def test_symmetric_brush_is_mirrored(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.4
    d, problems = apply_edits(arena, [_brush(x, z, tool="lower", amount=40.0)], symmetry=True)
    assert problems == []
    (ax, az), (bx, bz) = orbit(arena.sym, x, z)[:2]
    for px, pz in ((ax, az), (bx, bz)):
        iz, ix = _cell(d, px, pz)
        assert d.hm[iz, ix] == pytest.approx(arena.hm[iz, ix] - 40.0, abs=1.0)


def test_flatten_uses_one_target_for_the_whole_orbit(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.4
    d, problems = apply_edits(arena, [_brush(x, z, tool="flatten")], symmetry=True)
    assert problems == []
    iz, ix = _cell(d, x, z)
    target = float(arena.hm[iz, ix])
    (ax, az), (bx, bz) = orbit(arena.sym, x, z)[:2]
    ia, ib = _cell(d, ax, az), _cell(d, bx, bz)
    assert d.hm[ia] == pytest.approx(d.hm[ib], abs=1e-3)     # both sides flattened to the same height
    assert abs(d.hm[ib] - target) < abs(arena.hm[ib] - target) + 1e-3


def test_brush_on_symmetry_axis_is_a_problem(arena):
    x, z = arena.sym.W * 0.5, arena.sym.H * 0.2             # centre line of a mirror map: no mirror image
    d, problems = apply_edits(arena, [_brush(x, z)], symmetry=True)
    assert len(problems) == 1 and "symmetry axis" in problems[0]["reason"]
    assert np.array_equal(d.hm, arena.hm)


def test_brush_outside_map_is_a_problem(arena):
    d, problems = apply_edits(arena, [_brush(-100.0, 10.0)], symmetry=False)
    assert len(problems) == 1 and "outside" in problems[0]["reason"]


def test_undo_is_dropping_the_entry(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    edits = [_brush(x, z, amount=30.0), _brush(x, z, tool="smooth")]
    with_both, _ = apply_edits(arena, edits, symmetry=False)
    with_one, _ = apply_edits(arena, edits[:1], symmetry=False)
    none, _ = apply_edits(arena, [], symmetry=False)
    assert np.array_equal(none.hm, arena.hm)
    assert not np.array_equal(with_both.hm, with_one.hm)


def test_brush_edit_roundtrip_through_project_file(arena):
    edits = [_brush(300.0, 400.0, tool="flatten", target=120.0, strength=0.5),
             _brush(500.0, 200.0, tool="raise", amount=12.5, radius=300.0)]
    data = project.new_project("arena", {"size": 12}, seed=2, symmetry=True, edits=edits)
    back = project.loads(project.dumps(data))
    assert back["edits"] == edits
    assert back["version"] == project.CURRENT_VERSION
    assert project.dumps(back) == project.dumps(data)


def test_old_project_without_brushes_loads_unchanged():
    old = dict(format=project.FORMAT_ID, version=1, template="arena", values={"size": 12}, seed=2, symmetry=True,
               edits=[dict(op="add_mex", at=[100.0, 200.0], metal=2.0)])
    back = project.loads(project.dumps(old))
    assert back == old


@pytest.mark.parametrize("bad", [
    dict(op="brush", tool="dig", at=[1.0, 1.0], radius=100.0),
    dict(op="brush", tool="raise", at=[1.0, 1.0], radius=0),
    dict(op="brush", tool="raise", at=[1.0, 1.0], radius=100.0, strength=1.5),
    dict(op="brush", tool="raise", at="here", radius=100.0),
    dict(op="brush", tool="raise", at=[1.0, 1.0], radius=100.0, target=5.0),
])
def test_malformed_brush_edits_are_rejected(bad):
    with pytest.raises(ValueError):
        project.validate_edits([bad])
