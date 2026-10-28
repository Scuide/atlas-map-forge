"""Stamp edits: copy the heights of a rectangle and paste them elsewhere, turned, mirrored and blended; mirrored
with the symmetry, checked and saved in .forge.json."""
import dataclasses

import numpy as np
import pytest

from atlasforge import SQ, forge, project
from atlasforge.edits import apply_edits, stamp_patch
from atlasforge.symmetry import RotSymmetry

QUIET = dict(log=lambda *a: None)


@pytest.fixture(scope="module")
def arena():
    d = forge.make("arena", {"size": 12, "erosion": 0}, seed=2, **QUIET)
    rng = np.random.default_rng(0)                       # rough ground, so every cell of a copy is recognisable
    return dataclasses.replace(d, hm=(np.asarray(d.hm) + rng.uniform(0, 50, d.hm.shape)).astype(d.hm.dtype))


def _stamp(src_cells, to_cell, **kw):
    """Stamp of the cell rectangle (i0, j0, i1, j1) centred on cell to_cell (i, j)."""
    i0, j0, i1, j1 = src_cells
    e = dict(op="stamp", src=[j0 * SQ, i0 * SQ, j1 * SQ, i1 * SQ], to=[to_cell[1] * SQ, to_cell[0] * SQ])
    e.update(kw)
    return e


def _src(hm, i0, j0, i1, j1):
    return np.asarray(hm[i0:i1 + 1, j0:j1 + 1], np.float64)


def _dst(hm, ci, cj, h, w):
    ti, tj = ci - (h - 1) // 2, cj - (w - 1) // 2
    return np.asarray(hm[ti:ti + h, tj:tj + w], np.float64)


def test_stamp_copies_heights_exactly(arena):
    hm = np.asarray(arena.hm)
    d, problems = apply_edits(arena, [_stamp((20, 20, 30, 34), (60, 40))], symmetry=False)
    assert problems == []
    src = _src(hm, 20, 20, 30, 34)
    assert np.allclose(_dst(d.hm, 60, 40, *src.shape), src, atol=1e-3)
    assert np.array_equal(np.asarray(d.hm)[0:5, 0:5], hm[0:5, 0:5])          # elsewhere untouched
    assert np.array_equal(np.asarray(arena.hm), hm)                          # base design untouched


@pytest.mark.parametrize("rotate", [90, 180, 270])
def test_stamp_rotation_is_clockwise(arena, rotate):
    hm = np.asarray(arena.hm)
    d, problems = apply_edits(arena, [_stamp((20, 20, 30, 34), (60, 40), rotate=rotate)], symmetry=False)
    assert problems == []
    src = _src(hm, 20, 20, 30, 34)
    want = np.rot90(src, -rotate // 90)
    assert np.allclose(_dst(d.hm, 60, 40, *want.shape), want, atol=1e-3)
    if rotate == 90:                                    # clockwise on the map: the top-left corner goes top-right
        got = _dst(d.hm, 60, 40, *want.shape)
        assert got[0, -1] == pytest.approx(src[0, 0], abs=1e-3)
        assert got[0, 0] == pytest.approx(src[-1, 0], abs=1e-3)              # and the bottom-left goes top-left


def test_stamp_flip_then_rotate(arena):
    hm = np.asarray(arena.hm)
    d, _ = apply_edits(arena, [_stamp((20, 20, 30, 34), (60, 40), rotate=90, flip=True)], symmetry=False)
    want = np.rot90(_src(hm, 20, 20, 30, 34)[:, ::-1], -1)
    assert np.allclose(_dst(d.hm, 60, 40, *want.shape), want, atol=1e-3)


def test_stamp_blend_softens_the_edge(arena):
    hm = np.asarray(arena.hm)
    blend = 4 * SQ
    d, _ = apply_edits(arena, [_stamp((20, 20, 40, 40), (60, 40), blend=blend)], symmetry=False)
    src = _src(hm, 20, 20, 40, 40)
    got = _dst(d.hm, 60, 40, *src.shape)
    old = _dst(hm, 60, 40, *src.shape)
    assert np.allclose(got[6:-6, 6:-6], src[6:-6, 6:-6], atol=1e-3)         # inside the blend: an exact copy
    assert np.allclose(got[0], old[0], atol=1e-3)                          # border row: the old ground
    mid = got[2, 10]
    assert min(src[2, 10], old[2, 10]) - 1e-3 <= mid <= max(src[2, 10], old[2, 10]) + 1e-3
    _p, w = stamp_patch(hm, (20 * SQ, 20 * SQ, 40 * SQ, 40 * SQ), 0, False, blend)
    assert w[0, 10] == 0 and w[10, 10] == 1 and 0 < w[2, 10] < 1


def test_stamp_mirrors_with_symmetry(arena):
    sym = arena.sym
    d, problems = apply_edits(arena, [_stamp((20, 20, 30, 34), (60, 40), rotate=90)], symmetry=True)
    assert problems == []
    img = sym.mirror_grid(np.asarray(d.hm, np.float64))
    want = np.rot90(_src(arena.hm, 20, 20, 30, 34), -1)
    assert np.allclose(_dst(img, 60, 40, *want.shape), want, atol=1e-3)     # the mirror image holds the copy too


def test_stamp_rotates_with_ffa_symmetry(arena):
    n = min(arena.hm.shape)
    hm = np.asarray(arena.hm)[:n, :n]
    W = (n - 1) * SQ
    d0 = dataclasses.replace(arena, hm=hm, sym=RotSymmetry(4, W, W))
    d, problems = apply_edits(d0, [_stamp((10, 10, 18, 20), (n // 4, n // 2))], symmetry=True)
    assert problems == []
    out = np.asarray(d.hm, np.float64)
    want = _src(hm, 10, 10, 18, 20)
    assert np.allclose(_dst(out, n // 4, n // 2, *want.shape), want, atol=1e-3)
    for k in range(1, 4):                                 # each quarter turn of the map holds the copy, turned with it
        img = d0.sym.rotate_grid(out, -k)                 # turn image k back onto the original place
        assert np.allclose(_dst(img, n // 4, n // 2, *want.shape), want, atol=0.05)


def test_stamp_problems_and_validation(arena):
    W, H = arena.sym.W, arena.sym.H
    _d, problems = apply_edits(arena, [dict(op="stamp", src=[-50, 0, 200, 200], to=[400, 400])], symmetry=False)
    assert problems and "outside" in problems[0]["reason"]
    _d, problems = apply_edits(arena, [dict(op="stamp", src=[0, 0, 200, 200], to=[400, 400], rotate=45)])
    assert problems and "rotate" in problems[0]["reason"]
    _d, problems = apply_edits(arena, [dict(op="stamp", src=[0, 0, 200, 200], to=[W / 2, H / 2])], symmetry=True)
    assert problems                                          # the centre has no mirror image apart from itself
    _d, problems = apply_edits(arena, [dict(op="stamp", src=[0, 0, 200, 200], to=[W - 10, H - 10])],
                               symmetry=False)
    assert problems == []                                    # cut off at the border, not refused
    good = dict(op="stamp", src=[0, 0, 200, 200], to=[400, 400], rotate=180, flip=True, blend=32)
    assert project.validate_edits([good]) == [good]
    for bad in (dict(good, src=[0, 0, 4, 4]), dict(good, rotate=30), dict(good, flip=1), dict(good, blend=-1),
                dict(good, to=[1])):
        with pytest.raises(ValueError):
            project.validate_edits([bad])
