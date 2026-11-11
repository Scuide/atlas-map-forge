"""Target game Beyond All Reason: metal map values, lava file, wrecks, Zero-K-only gadgets, start box commands."""
import re
import struct
import zipfile

import numpy as np
import pytest

from atlasforge import forge, games
from atlasforge.config import ForgeConfig
from atlasforge.gadgets import lava_config

QUIET = dict(log=lambda *a: None)


def test_bar_metal_map_sums_to_spot_metal():
    mexes = [dict(x=1000.0, z=1200.0, metal=2.0), dict(x=3000.0, z=500.0, metal=3.5)]
    mm = games.bar_metal_map((256, 256), mexes)
    for m in mexes:
        assert games.bar_spot_metal(mm, m["x"], m["z"]) == pytest.approx(m["metal"], abs=0.03)
    assert mm.max() <= 255


def test_bar_lava_from_zero_k_config():
    zk = lava_config(46, calm_s=170, high_s=40, rise_speed=0.1, fall_speed=0.08, damage=160)
    bar = games.bar_lava_lua(zk)
    assert "damage = 160" in bar and "level = 1" in bar
    rows = re.findall(r"\{ (-?[\d.]+), ([\d.]+), ([\d.]+) \}", bar)
    # starts calm (one elmo under the start level), then rises to 46 and holds 40 s
    assert [tuple(float(v) for v in r) for r in rows] == [(0, 2.4, 170), (46, 3, 40)]


def test_bar_files_and_features():
    files = {"mapconfig/chicken_zones.lua": "x", "LuaRules/Gadgets/map_chicken_zones.lua": "y",
             "mapconfig/lava_config.lua": lava_config(30), "features/forge_rocks.lua": "z"}
    out = games.bar_files(files)
    assert "mapconfig/chicken_zones.lua" not in out and "LuaRules/Gadgets/map_chicken_zones.lua" not in out
    assert "mapconfig/lava.lua" in out and "mapconfig/lava_config.lua" in out and "features/forge_rocks.lua" in out
    feats = games.bar_features([("tankriot_dead", 1.0, 2.0, 0.0), ("rock_a", 3.0, 4.0, 0.0)])
    assert feats == [("corlevlr_dead", 1.0, 2.0, 0.0), ("rock_a", 3.0, 4.0, 0.0)]


def test_bar_box_commands():
    src = """return {
\t[0] = { nameLong = "West", nameShort = "W", startpoints = { {500, 3000} }, boxes = { { {0, 1000}, {1200, 1000}, {1200, 5000}, {0, 5000} } } },
\t[1] = { nameLong = "East", nameShort = "E", startpoints = { {5644, 3000} }, boxes = { { {4944, 1000}, {6144, 1000}, {6144, 5000}, {4944, 5000} } } },
}"""
    assert games.bar_box_commands(src, 6144, 6144) == ["!addBox 0 32 40 163 1", "!addBox 160 32 200 163 2"]


def test_config_game():
    with pytest.raises(ValueError):
        ForgeConfig(game="supcom").validate()
    assert ForgeConfig(game="bar").validate().game == "bar"


def test_chicken_maps_are_zero_k_only(tmp_path):
    d = forge.make("chicken", {"size": 16, "erosion": 0}, seed=1, **QUIET)
    with pytest.raises(ValueError, match="Zero-K only"):
        forge.build(d, outdir=str(tmp_path), config=ForgeConfig(author="T"), game="bar", **QUIET)


def test_build_for_bar(tmp_path):
    d = forge.make("chokepoint", {"size": 12, "erosion": 0, "grass": 0, "rocks": 0, "wrecks": 0.6}, seed=2, **QUIET)
    info = forge.build(d, outdir=str(tmp_path), config=ForgeConfig(author="T"), game="bar", preview=False, **QUIET)
    assert info["game"] == "bar"
    with zipfile.ZipFile(info["path"]) as z:
        mi = z.read("mapinfo.lua").decode()
        smf = z.read([n for n in z.namelist() if n.endswith(".smf")][0])
    assert re.search(r"maxmetal\s*=\s*1,", mi)
    h = struct.unpack("<16s7i2f7i", smf[:80])
    nx, nz, metal_ptr = h[3], h[4], h[14]
    mm = np.frombuffer(smf[metal_ptr:metal_ptr + (nx // 2) * (nz // 2)], np.uint8).reshape(nz // 2, nx // 2)
    for m in d.mexes[:8]:
        assert games.bar_spot_metal(mm, m["x"], m["z"]) == pytest.approx(m["metal"], abs=0.05)
    names = set(re.findall(rb"[a-z]+_dead", smf))
    assert names and all(n.startswith((b"arm", b"cor")) for n in names)


def test_install_bar_lobby_pictures(tmp_path):
    from atlasforge.install import install
    d = forge.make("skirmish", {"size": 8, "erosion": 0, "rocks": 0, "wrecks": 0}, seed=3, **QUIET)
    info = forge.build(d, outdir=str(tmp_path / "out"), config=ForgeConfig(author="T"), game="bar", preview=False, **QUIET)
    bar = tmp_path / "bar"
    install(info["path"], str(bar), lobby="byar", log=lambda *a: None)
    base = bar / "LuaMenu" / "configs" / "gameConfig" / "byar"
    assert (bar / "maps" / info["file"]).exists()
    assert list((base / "minimapOverride").glob("*.jpg")) and list((base / "minimapThumbnail").glob("*.png"))
