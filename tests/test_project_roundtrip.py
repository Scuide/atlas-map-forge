"""Round trip of a .forge.json that holds one edit of every edit type: saved, loaded again and applied, the heights,
features and paint textures are identical. An old project file without the newer fields still loads and applies."""
import hashlib
import json

import pytest

from atlasforge import forge, project
from atlasforge.edits import apply_edits

QUIET = dict(log=lambda *a: None)


@pytest.fixture(scope="module")
def arena():
    return forge.make("arena", {"size": 12, "erosion": 0}, seed=2, **QUIET)


def _all_types(d):
    W, H = d.sym.W, d.sym.H
    return [
        dict(op="brush", tool="raise", at=[0.2 * W, 0.2 * H], radius=300.0, strength=0.5),
        dict(op="brush", tool="noise", at=[0.3 * W, 0.2 * H], radius=300.0, strength=0.8, amount=40.0, seed=3),
        dict(op="brush", tool="terrace", at=[0.4 * W, 0.2 * H], radius=300.0, strength=1.0, amount=30.0),
        dict(op="brush", tool="ramp", at=[0.2 * W, 0.4 * H], to=[0.3 * W, 0.4 * H], radius=200.0, strength=0.7),
        dict(op="brush", tool="flatten", at=[0.4 * W, 0.4 * H], radius=300.0, strength=0.6, target=120.0),
        dict(op="paint", material="concrete", points=[[0.2 * W, 0.6 * H], [0.3 * W, 0.6 * H]],
             radius=150.0, strength=1.0),
        dict(op="paint", material="path", fill="poly", points=[[0.4 * W, 0.6 * H], [0.5 * W, 0.6 * H],
                                                               [0.45 * W, 0.7 * H]], strength=1.0),
        dict(op="paint", material="erase", points=[[0.2 * W, 0.6 * H], [0.3 * W, 0.6 * H]],
             radius=60.0, strength=1.0),
        dict(op="features", kind="trees", mode="add", at=[0.7 * W, 0.2 * H], radius=400.0, density=1.0),
        dict(op="features", kind="rocks", mode="add", at=[0.7 * W, 0.5 * H], radius=300.0, density=1.0),
        dict(op="features", kind="wrecks", mode="add", at=[0.7 * W, 0.8 * H], radius=300.0, density=1.0),
        dict(op="stamp", src=[200, 200, 600, 600], to=[0.55 * W, 0.92 * H], rotate=90),
        dict(op="add_mex", at=[0.1 * W, 0.5 * H], metal=2.0),
        dict(op="set_metal", at=[0.1 * W, 0.5 * H], metal=3.0),
        dict(op="brush", tool="raise", at=[0.6 * W, 0.4 * H], radius=300.0, strength=1.0, enabled=False),
    ]


def _state(d):
    """Heights, features and a hash of the paint layers (the texture)."""
    tex = hashlib.sha256()
    for k in sorted(d.paint or {}):
        tex.update(k.encode())
        tex.update(d.paint[k].tobytes())
    return dict(hm=d.hm.tobytes(), features=repr(d.features), tex=tex.hexdigest(), mexes=repr(d.mexes))


def test_every_edit_type_survives_save_and_load(arena, tmp_path):
    edits = _all_types(arena)
    d1, problems = apply_edits(arena, edits, symmetry=True)
    assert problems == []
    assert _state(d1)["tex"] != _state(arena)["tex"]                 # paint changed the texture

    path = tmp_path / "all.forge.json"
    data = project.new_project(arena.template, {"size": 12, "erosion": 0}, 2, True, edits, "All types")
    project.save(str(path), data)
    loaded = project.load(str(path))
    assert loaded["edits"] == edits

    d2, problems = apply_edits(arena, loaded["edits"], symmetry=loaded["symmetry"])
    assert problems == []
    assert _state(d2) == _state(d1)


def test_disabled_edit_is_kept_but_not_applied(arena):
    last = _all_types(arena)[-1]
    off, problems = apply_edits(arena, [last])
    assert problems == [] and off.hm.tobytes() == arena.hm.tobytes()


def test_old_project_file_without_new_fields_loads(arena):
    old = dict(format=project.FORMAT_ID, version=1, template=arena.template, values={"size": 12, "erosion": 0},
               seed=2, symmetry=True, edits=[
                   dict(op="add_mex", at=[0.1 * arena.sym.W, 0.5 * arena.sym.H], metal=2.0),
                   dict(op="brush", tool="raise", at=[0.2 * arena.sym.W, 0.2 * arena.sym.H], radius=300.0,
                        strength=0.5),
                   dict(op="paint", material="concrete", points=[[0.2 * arena.sym.W, 0.6 * arena.sym.H],
                                                                 [0.3 * arena.sym.W, 0.6 * arena.sym.H]],
                        radius=150.0),
               ], title="Old")
    text = json.dumps(old)
    loaded = project.loads(text)
    project.validate(loaded)
    assert all("enabled" not in e and "fill" not in e for e in loaded["edits"])
    d, problems = apply_edits(arena, loaded["edits"], symmetry=loaded["symmetry"])
    assert problems == []
    assert _state(d)["tex"] != _state(arena)["tex"]
