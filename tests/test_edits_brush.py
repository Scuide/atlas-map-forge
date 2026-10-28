"""Brush edits (editor stage B): terrain brushes stored in the edit list, applied to the height map before the build,
mirrored with the symmetry, undone by dropping the entry, and saved in .forge.json without changing old files."""
import numpy as np
import pytest

from atlasforge import SQ, forge, project
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


def _ramp(a, b, **kw):
    e = dict(op="brush", tool="ramp", at=list(a), to=list(b), radius=200.0, strength=1.0)
    e.update(kw)
    return e


def test_ramp_edit_runs_from_height_of_a_to_height_of_b(arena):
    a = (arena.sym.W * 0.3, arena.sym.H * 0.4)
    b = (arena.sym.W * 0.6, arena.sym.H * 0.4)
    d, problems = apply_edits(arena, [_ramp(a, b)], symmetry=False)
    assert problems == []
    ia, ib = _cell(d, *a), _cell(d, *b)
    assert d.hm[ia] == pytest.approx(arena.hm[ia], abs=SQ)       # w == 1 at A and B: the ground there is kept
    assert d.hm[ib] == pytest.approx(arena.hm[ib], abs=SQ)
    assert not np.array_equal(d.hm, arena.hm)                     # the strip between them changed


def test_symmetric_ramp_is_mirrored(arena):
    a = (arena.sym.W * 0.3, arena.sym.H * 0.4)
    b = (arena.sym.W * 0.4, arena.sym.H * 0.2)          # the two strips do not cross: each end keeps its own ground
    d, problems = apply_edits(arena, [_ramp(a, b)], symmetry=True)
    assert problems == []
    (ax, az), (ax2, az2) = orbit(arena.sym, *a)[:2]
    (bx, bz), (bx2, bz2) = orbit(arena.sym, *b)[:2]
    for pa, pb in (((ax, az), (bx, bz)), ((ax2, az2), (bx2, bz2))):
        assert d.hm[_cell(d, *pa)] == pytest.approx(arena.hm[_cell(d, *pa)], abs=SQ)   # cell grid: within one cell
        assert d.hm[_cell(d, *pb)] == pytest.approx(arena.hm[_cell(d, *pb)], abs=SQ)


def test_ramp_with_same_start_and_end_is_a_problem(arena):
    d, problems = apply_edits(arena, [_ramp((300.0, 300.0), (300.0, 300.0))], symmetry=False)
    assert len(problems) == 1 and "two different points" in problems[0]["reason"]
    assert np.array_equal(d.hm, arena.hm)


def test_ramp_roundtrip_through_project_file(arena):
    edits = [_ramp((300.0, 400.0), (700.0, 250.0), radius=160.0, strength=0.6)]
    data = project.new_project("arena", {"size": 12}, seed=2, symmetry=True, edits=edits)
    back = project.loads(project.dumps(data))
    assert back["edits"] == edits
    assert project.dumps(back) == project.dumps(data)


@pytest.mark.parametrize("bad", [
    dict(op="brush", tool="ramp", at=[1.0, 1.0], radius=100.0),                  # no end point
    dict(op="brush", tool="ramp", at=[1.0, 1.0], to="there", radius=100.0),
    dict(op="brush", tool="raise", at=[1.0, 1.0], to=[5.0, 5.0], radius=100.0),  # to: ramp only
])
def test_malformed_ramp_edits_are_rejected(bad):
    with pytest.raises(ValueError):
        project.validate_edits([bad])


def _noise(x, z, **kw):
    e = dict(op="brush", tool="noise", at=[x, z], radius=600.0, strength=1.0, amount=30.0, seed=7)
    e.update(kw)
    return e


def test_noise_is_deterministic_and_seed_dependent(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    a, _ = apply_edits(arena, [_noise(x, z)], symmetry=False)
    b, _ = apply_edits(arena, [_noise(x, z)], symmetry=False)
    c, _ = apply_edits(arena, [_noise(x, z, seed=8)], symmetry=False)
    assert np.array_equal(a.hm, b.hm)                        # same edit, same relief
    assert not np.array_equal(a.hm, c.hm)                    # another seed, another pattern
    assert not np.array_equal(a.hm, arena.hm)


def test_noise_stays_within_amount_at_the_centre(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    d, problems = apply_edits(arena, [_noise(x, z, amount=30.0)], symmetry=False)
    assert problems == []
    delta = np.abs(d.hm - arena.hm)
    assert delta.max() <= 30.0 + 1e-6                        # n in [-1, 1], w in [0, 1]
    assert delta.max() > 1.0                                 # and it does roughen


def test_symmetric_noise_uses_the_same_relief_at_every_mirror_image(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.4
    d, problems = apply_edits(arena, [_noise(x, z, amount=30.0)], symmetry=True)
    assert problems == []
    deltas = []
    for px, pz in orbit(arena.sym, x, z)[:2]:
        iz, ix = _cell(d, px, pz)
        deltas.append(d.hm[iz, ix] - arena.hm[iz, ix])
    assert deltas[0] == pytest.approx(deltas[1], abs=1e-3)   # the centre cell gets the same value on both sides


def test_terrace_snaps_the_centre_to_steps(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    step = 24.0
    d, problems = apply_edits(arena, [_brush(x, z, tool="terrace", amount=step)], symmetry=False)
    assert problems == []
    iz, ix = _cell(d, x, z)
    assert d.hm[iz, ix] == pytest.approx(round(arena.hm[iz, ix] / step) * step, abs=0.5)   # w ~ 1 at the centre


def test_symmetric_terrace_steps_both_sides_alike(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.4
    d, problems = apply_edits(arena, [_brush(x, z, tool="terrace", amount=16.0)], symmetry=True)
    assert problems == []
    (ax, az), (bx, bz) = orbit(arena.sym, x, z)[:2]
    ia, ib = _cell(d, ax, az), _cell(d, bx, bz)
    assert d.hm[ia] == pytest.approx(round(arena.hm[ia] / 16.0) * 16.0, abs=0.5)
    assert d.hm[ib] == pytest.approx(round(arena.hm[ib] / 16.0) * 16.0, abs=0.5)


def test_noise_and_terrace_survive_the_project_file(arena):
    edits = [_noise(arena.sym.W * 0.3, arena.sym.H * 0.5, stroke=3),
             _brush(arena.sym.W * 0.6, arena.sym.H * 0.5, tool="terrace", amount=12.0)]
    assert project.validate_edits(edits) == edits


@pytest.mark.parametrize("bad", [
    dict(op="brush", tool="terrace", at=[1.0, 1.0], radius=100.0, amount=0.0),
    dict(op="brush", tool="terrace", at=[1.0, 1.0], radius=100.0, amount=-4.0),
    dict(op="brush", tool="noise", at=[1.0, 1.0], radius=100.0, seed=-1),
    dict(op="brush", tool="noise", at=[1.0, 1.0], radius=100.0, seed=1.5),
    dict(op="brush", tool="raise", at=[1.0, 1.0], radius=100.0, seed=3),
])
def test_malformed_noise_and_terrace_edits_are_rejected(bad):
    with pytest.raises(ValueError):
        project.validate_edits([bad])
