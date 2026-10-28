"""Paint edits (editor stage C): texture strokes stored in the edit list, mirrored with the symmetry, visible in the
rendered texture and the quick preview, and saved in .forge.json."""
import numpy as np
import pytest

from atlasforge import SQ, TEX_PER_SQ, forge, project
from atlasforge.edits import apply_edits
from atlasforge.render import NoiseBank, PAINT_LAYERS, build_texture_fields, render_rgb
from atlasforge.symmetry import orbit

QUIET = dict(log=lambda *a: None)


@pytest.fixture(scope="module")
def arena():
    return forge.make("arena", {"size": 12, "erosion": 0}, seed=2, **QUIET)


def _paint(points, material="concrete", **kw):
    e = dict(op="paint", material=material, points=[list(p) for p in points], radius=120.0, strength=1.0)
    e.update(kw)
    return e


def _cell(x, z):
    return int(round(z / SQ)), int(round(x / SQ))


def test_paint_sets_layer_and_keeps_base(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    had = None if arena.paint is None else dict(arena.paint)
    d, problems = apply_edits(arena, [_paint([(x, z), (x + 200, z)])], symmetry=False)
    assert problems == []
    iz, ix = _cell(x + 100, z)
    assert d.paint["concrete"][iz, ix] == pytest.approx(1.0)
    assert d.paint["concrete"][_cell(x + 100, z + 400)] == 0           # far away stays clean
    assert 0 < d.paint["concrete"][_cell(x, z + 100)] < 1               # soft edge
    assert (arena.paint is None) == (had is None)                       # base design untouched
    if had is not None:
        assert "concrete" not in arena.paint or arena.paint["concrete"] is had.get("concrete")


def test_symmetric_stroke_is_mirrored(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.4
    d, problems = apply_edits(arena, [_paint([(x, z), (x, z + 100)], "scorch")], symmetry=True)
    assert problems == []
    (ax, az), (bx, bz) = orbit(arena.sym, x, z + 50)[:2]
    for px, pz in ((ax, az), (bx, bz)):
        assert d.paint["scorch"][_cell(px, pz)] > 0.9


@pytest.mark.parametrize("bad", [
    _paint([(100, 100)], material="mud"),
    _paint([]),
    _paint([(100, 100)], radius=0),
    _paint([(100, 100)], strength=0),
    _paint([(100, 100)], strength=2),
    _paint([(-50, 100)]),
])
def test_bad_stroke_is_reported_not_raised(arena, bad):
    d, problems = apply_edits(arena, [bad], symmetry=False)
    assert len(problems) == 1 and problems[0]["index"] == 0


def test_stroke_changes_texture_pixels_and_preview(arena):
    x, z = arena.sym.W * 0.3, arena.sym.H * 0.5
    d, _ = apply_edits(arena, [_paint([(x, z), (x + 200, z)], "lava")], symmetry=False)
    wpx = (d.hm.shape[1] - 1) * TEX_PER_SQ
    row = int(z / SQ * TEX_PER_SQ)
    NB = NoiseBank(np.random.default_rng(1))

    def strip(des):
        F = build_texture_fields(des.hm)
        if des.paint:
            F["paint"] = np.dstack([np.clip(des.paint.get(k, np.zeros(des.hm.shape, np.float32)), 0, 1)
                                    for k in PAINT_LAYERS]).astype(np.float32)
            from atlasforge.render import crack_field
            F["crack"] = crack_field(des.hm.shape[0], np.random.default_rng(3))
        return render_rgb(F, row, row + 4, wpx, des.biome, 0.0, NB, [])

    base, painted = strip(arena), strip(d)
    col = int((x + 100) / SQ * TEX_PER_SQ)
    assert not np.array_equal(base[:, col], painted[:, col])
    assert np.array_equal(base[:, 0], painted[:, 0])                    # left border is not touched
    p0 = np.asarray(forge.preview(arena, size=256))
    p1 = np.asarray(forge.preview(d, size=256))
    assert not np.array_equal(p0, p1)


def test_paint_survives_project_roundtrip():
    edits = [_paint([(500, 500), (900, 700)], "path", radius=60.0, strength=0.6)]
    p = project.new_project("arena", {"size": 12}, 2, True, edits, "t", "0.0")
    q = project.loads(project.dumps(p))
    assert q["edits"] == edits
