"""Target games. Zero-K is the default; Beyond All Reason (BAR) runs on the same engine (Recoil) and reads
the same map format, with these differences (checked against BAR test-31908, engine 2026.07.04):

- Metal: BAR finds metal spots in the SMF metal map (common/upgets/api_resource_spot_finder.lua). A spot's
  worth is the sum of GetMetalAmount over its cells, GetMetalAmount = pixel * maxmetal, and the game shows
  (and a T1 extractor earns) worth / 1000 per second (luaui/widgets/gui_metalspots.lua). Measured in game:
  pixel sums for "2.0" with pixel/255 scaling showed 0.5. So every BAR spot gets a disc of pixels with
  sum(pixel) * maxmetal / 1000 = its metal value (Zero-K reads mapconfig/map_metal_layout.lua and the metal
  map only marks where spots are).
- Lobby pictures: Chobby for BAR reads LuaMenu/configs/gameConfig/byar/minimapOverride/<name>.jpg and
  minimapThumbnail/<name>.png from the data folder, like Zero-K's Chobby with .../zk/....
- Lava: BAR's map_lava.lua reads mapconfig/lava.lua (tideRhythm rows {level, elmos per second, seconds});
  Zero-K reads mapconfig/lava_config.lua (tideRhym rows {target, elmos per frame, seconds}).
- Wrecks: BAR unit corpses are <unit>_dead of BAR units.
- Start boxes: BAR does not read them from the map (they come from BAR's map database or the lobby);
  start positions in mapinfo.lua still apply.
- Chicken defence (co-op templates) is Zero-K only; BAR has its own Raptors and Scavengers.
"""
import math
import os
import re
import sys

import numpy as np

GAMES = {"zk": "Zero-K", "bar": "Beyond All Reason"}
DEFAULT = "zk"

BAR_MAXMETAL = 1.0           # mapinfo maxmetal for BAR maps (GetMetalAmount = pixel * maxmetal)
BAR_SPOT_RADIUS = 40.0       # elmos: metal map cells within this radius form a spot (as for Zero-K)
BAR_METAL_SCALE = 1.0        # Zero-K spot metal -> BAR spot metal (calibrate after an in-game test)

# Zero-K wreck -> BAR wreck with a similar amount of metal (BAR metal in the comment)
BAR_WRECKS = {
    "cloakraid_dead": "armpw_dead",          # 29
    "shieldraid_dead": "corak_dead",         # 22
    "vehraid_dead": "armflash_dead",         # 71
    "hoverraid_dead": "armrock_dead",        # 63
    "cloakskirm_dead": "corstorm_dead",      # 55
    "vehsupport_dead": "corgator_dead",      # 77
    "cloakriot_dead": "armham_dead",         # 79
    "shieldriot_dead": "corthud_dead",       # 96
    "spiderriot_dead": "cormort_dead",       # 118
    "vehassault_dead": "armjanus_dead",      # 147
    "jumpskirm_dead": "armfido_dead",        # 164
    "tankraid_dead": "armstump_dead",        # 152
    "hoverriot_dead": "armwar_dead",         # 161
    "tankriot_dead": "corlevlr_dead",        # 190
    "tankassault_dead": "correap_dead",      # 350
    "jumpassault_dead": "corcan_dead",       # 339
    "tankarty_dead": "armsnipe_dead",        # 322
    "striderdante_dead": "armfboy_dead",     # 1008
    "striderscorpion_dead": "corsumo_dead",  # 1118
}

ZK_ONLY_FILES = ("LuaRules/Gadgets/map_chicken_zones.lua", "mapconfig/chicken_zones.lua")


def name(game):
    return GAMES.get(game or DEFAULT, GAMES[DEFAULT])


def check(game):
    if (game or DEFAULT) not in GAMES:
        raise ValueError(f"Unknown game {game!r}; use one of: {', '.join(GAMES)}")
    return game or DEFAULT


def zk_only(template):
    """Templates that only work in Zero-K (chicken defence)."""
    return "coop" in getattr(template, "modes", ())


# ----------------------------------------------------------------------------- metal
def bar_metal_map(shape, mexes):
    """uint8 metal map (16-elmo cells) for BAR: per spot a disc whose pixels add up to the spot's metal."""
    nz2, nx2 = shape
    metal = np.zeros(shape, np.float64)
    mi, mj = np.mgrid[0:nz2, 0:nx2]
    for m in mexes:
        disc = np.hypot(mi * 16 + 8 - m["z"], mj * 16 + 8 - m["x"]) < BAR_SPOT_RADIUS
        n = int(disc.sum())
        if n:
            metal[disc] += m["metal"] * BAR_METAL_SCALE * 1000 / (BAR_MAXMETAL * n)
    return np.clip(np.round(metal), 0, 255).astype(np.uint8)


def bar_spot_metal(metal_map, x, z):
    """Metal per second BAR shows for the spot at (x, z): sum of pixel * maxmetal around it / 1000."""
    nz2, nx2 = metal_map.shape
    mi, mj = np.mgrid[0:nz2, 0:nx2]
    disc = np.hypot(mi * 16 + 8 - z, mj * 16 + 8 - x) < BAR_SPOT_RADIUS
    return float(metal_map[disc].sum()) * BAR_MAXMETAL / 1000


# ----------------------------------------------------------------------------- lava
def bar_lava_lua(zk_conf):
    """Turn a Zero-K mapconfig/lava_config.lua (as written by gadgets.lava_config) into BAR's
    mapconfig/lava.lua. Zero-K starts at the second tide entry (calm), so BAR gets the entries rotated:
    the first row is one elmo under the start level, as BAR's map_lava.lua expects."""
    num = lambda key, default: float(m.group(1)) if (m := re.search(rf"\b{key}\s*=\s*(-?[\d.]+)", zk_conf)) else default
    level = num("level", 1)
    damage = num("damage", 100)
    rows = [tuple(float(v) for v in r) for r in re.findall(
        r"target\s*=\s*(-?[\d.]+)\s*,\s*speed\s*=\s*([\d.]+)\s*,\s*period\s*=\s*([\d.]+)", zk_conf)]
    if len(rows) >= 2:
        rows = rows[1:] + rows[:1]                     # Zero-K plays entry 2 first
    tide = []
    for target, speed, period in rows:
        tide.append((max(0.0, target - 1) if not tide else target, max(0.5, speed * 30), period))
    lines = ",\n".join(f"\t\t{{ {t:g}, {s:g}, {p:g} }}" for t, s, p in tide) or "\t\t{ 0, 1.5, 30000 }"
    return f"""-- Atlas Map Forge: lava for Beyond All Reason (LuaRules/Gadgets/map_lava.lua reads mapconfig/lava.lua).
-- tideRhythm rows: {{ lava height (elmos), speed (elmos per second), seconds until the next row }}
local conf = {{
\tlevel = {level:g},
\tdamage = {damage:g},
\ttideAmplitude = 2,
\ttidePeriod = 120,
\tcolorCorrection = "vec3(1.1, 1.0, 0.88)",
\tcoastColor = "vec3(2.2, 0.4, 0.0)",
\tcoastLightBoost = 0.7,
\tcoastWidth = 30.0,
\tfogFactor = 0.07,
\tfogColor = "vec3(2.0, 0.31, 0.0)",
\tfogHeight = 20,
\tfogAbove = 0.18,
\ttideRhythm = {{
{lines},
\t}},
}}
return conf
"""


def bar_files(files):
    """Map archive extra files for BAR: drop Zero-K-only gadgets, add BAR's lava file next to Zero-K's
    (the tide warning gadget keeps reading lava_config.lua)."""
    out = {k: v for k, v in (files or {}).items() if k not in ZK_ONLY_FILES}
    zk = out.get("mapconfig/lava_config.lua")
    if zk is not None:
        out["mapconfig/lava.lua"] = bar_lava_lua(zk.decode() if isinstance(zk, bytes) else zk)
    return out


def bar_features(features):
    """Rename Zero-K wrecks to BAR wrecks; other features (rocks, hedge trees) stay."""
    return [(BAR_WRECKS.get(f[0], f[0]),) + tuple(f[1:]) for f in (features or [])]


# ----------------------------------------------------------------------------- install folder
def find_bar():
    """Candidate BAR data folders (the folder with maps/ and engine/), best first."""
    cands = []
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local"))
        cands += [os.path.join(local, "Programs", "Beyond-All-Reason", "data"),
                  os.path.join(os.path.expanduser("~"), "Documents", "Beyond All Reason")]
    else:
        state = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        cands += [os.path.join(state, "Beyond All Reason"), os.path.expanduser("~/Documents/Beyond All Reason"),
                  os.path.expanduser("~/.local/share/Beyond All Reason")]
    out = []
    for c in cands:
        c = os.path.normpath(c)
        if c not in out and os.path.isdir(c) and (os.path.isdir(os.path.join(c, "maps"))
                                                    or os.path.isdir(os.path.join(c, "engine"))):
            out.append(c)
    return out


def bar_box_commands(startboxes_src, W, H):
    """Start boxes for the BAR lobby host: one "!addBox left top right bottom team" line per team, in
    BAR's 0..200 coordinates, the bounding box of the team's boxes in map_startboxes.lua."""
    from .app.luatable import startboxes
    out = []
    for b in startboxes(startboxes_src):
        pts = [p for poly in b["polygons"] for p in poly]
        if not pts:
            continue
        x0, x1 = min(p[0] for p in pts) / W, max(p[0] for p in pts) / W
        z0, z1 = min(p[1] for p in pts) / H, max(p[1] for p in pts) / H
        c = lambda v, f: int(min(200, max(0, f(v * 200))))
        out.append(f"!addBox {c(x0, math.floor)} {c(z0, math.floor)} {c(x1, math.ceil)} {c(z1, math.ceil)} {b['team'] + 1}")
    return out
