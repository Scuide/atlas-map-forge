"""Feature edits (editor stage C): add or remove trees in a disc, applied before the build and kept in the edit list,
mirrored with the symmetry."""
import math

import numpy as np
import pytest

from atlasforge import SQ, forge
from atlasforge.edits import apply_edits

QUIET = dict(log=lambda *a: None)


@pytest.fixture(scope="module")
def arena():
    return forge.make("arena", {"size": 12, "erosion": 0}, seed=2, **QUIET)


def _feat(x, z, r=600.0, mode="add", **kw):
    e = dict(op="features", kind="trees", mode=mode, at=[x, z], radius=r, density=kw.pop("density", 1.0))
    e.update(kw)
    return e


def _trees(d):
    return [f for f in d.features if f[0].startswith("treetype")]


def test_add_trees_places_trees_in_the_disc(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    before = len(_trees(arena))
    d, problems = apply_edits(arena, [_feat(x, z)], symmetry=False)
    assert not problems
    added = _trees(d)
    assert len(added) > 0
    assert all(math.hypot(f[1] - x, f[2] - z) <= 600.0 + 1e-6 for f in added)
    assert len(_trees(arena)) == before                      # the input design is not modified


def test_add_trees_is_symmetric(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    d, problems = apply_edits(arena, [_feat(x, z)], symmetry=True)
    assert not problems
    pts = [(f[1], f[2]) for f in _trees(d)]
    for px, pz in pts:
        mx, mz = arena.sym.mirror(px, pz)
        assert min(math.hypot(mx - qx, mz - qz) for qx, qz in pts) < 1e-6


def test_remove_blocks_trees_in_the_disc_and_drops_added_ones(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    added, _ = apply_edits(arena, [_feat(x, z)], symmetry=False)
    d, problems = apply_edits(arena, [_feat(x, z)] + [_feat(x, z, mode="remove")], symmetry=False)
    assert not problems
    assert not [f for f in _trees(d) if math.hypot(f[1] - x, f[2] - z) <= 600.0]
    assert d.tree_block is not None
    i, j = int(round(z / SQ)), int(round(x / SQ))
    assert d.tree_block[i, j]
    assert len(_trees(added)) > 0


def test_remove_then_add_elsewhere(arena):
    x1, z1 = arena.sym.W * 0.3, arena.sym.H * 0.5
    x2, z2 = arena.sym.W * 0.6, arena.sym.H * 0.5
    edits = [_feat(x1, z1, mode="remove"), _feat(x2, z2)]
    d, problems = apply_edits(arena, edits, symmetry=False)
    assert not problems
    assert len([f for f in _trees(d) if math.hypot(f[1] - x2, f[2] - z2) <= 600.0]) > 0


def test_bad_features_edit_is_a_problem_not_an_error(arena):
    d, problems = apply_edits(arena, [dict(op="features", mode="grow", at=[1, 1], radius=10)], symmetry=False)
    assert problems and "mode" in problems[0]["reason"]
    d, problems = apply_edits(arena, [_feat(1, 1, kind="rocks")], symmetry=False)
    assert problems and "kind" in problems[0]["reason"]


def test_density_zero_adds_nothing(arena):
    d, problems = apply_edits(arena, [_feat(arena.sym.W * 0.3, arena.sym.H * 0.5, density=0.0)], symmetry=False)
    assert not problems
    assert len(_trees(d)) == len(_trees(arena))


def test_project_file_keeps_feature_edits():
    from atlasforge import project
    edits = [_feat(100.0, 200.0), _feat(300.0, 200.0, mode="remove")]
    assert project.validate_edits(edits) == edits
    with pytest.raises(ValueError, match="mode"):
        project.validate_edits([_feat(100.0, 200.0, mode="grow")])
    with pytest.raises(ValueError, match="density"):
        project.validate_edits([_feat(100.0, 200.0, density=2)])
