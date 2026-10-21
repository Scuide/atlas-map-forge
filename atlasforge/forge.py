"""Pipeline: template -> design -> check report -> quick preview -> map archive.

    from atlasforge import forge
    d = forge.make("chokepoint", {"gates": 3}, seed=7)
    ok, lines = forge.check(d)
    forge.preview(d).save("preview.png")
    info = forge.build(d, outdir="out")
"""
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import SQ
from .archive import build_archive
from .checks import report
from .config import ForgeConfig
from .noise import smoothstep


def make(template_id, values=None, seed=1, log=print):
    from .templates import get
    t = get(template_id)
    v = t.resolve(values)
    t0 = time.time()
    d = t.make(v, seed, log)
    d.template = template_id
    d.values = v
    d.seed = seed
    log(f"  design ready in {time.time() - t0:.1f} s")
    return d


def check(design):
    """-> (ok, lines). Movement-class reachability, chokes, metal spots, plus the template's own checks."""
    t0, t1 = design.teams[0], design.teams[1]
    ok, lines = report(design.hm, t0, t1, design.mexes, design.gates, design.blocked, design.side_labels[1])
    lines = lines + list(design.notes)
    return ok and design.notes_ok, lines


# ----------------------------------------------------------------------------- quick preview
def _relief_colors(hm, biome, paint, size):
    """Fast stylised render of the heightmap (no texture pass): biome colours, slope rock, water,
    paint layers and hill shading."""
    n = hm.shape[0]
    zoom = size / (n - 1)
    h = ndimage.zoom(hm, zoom, order=1)[:size, :size] if zoom != 1 else hm[:size, :size]
    step = SQ / zoom
    gz, gx = np.gradient(h, step)
    slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    C = {k: np.array(biome[k], np.float32) for k in ("bed", "shore", "low", "mid", "high", "rock", "cliff", "peak")}
    t = np.clip(h / 340.0, 0, 1.2)
    col = C["low"] + (C["mid"] - C["low"]) * smoothstep(0.18, 0.5, t)[..., None]
    col = col + (C["high"] - col) * smoothstep(0.5, 0.85, t)[..., None]
    col = col + (C["peak"] - col) * smoothstep(biome["peak_level"] - 0.04, biome["peak_level"] + 0.04, t)[..., None]
    col = col + (C["rock"] - col) * smoothstep(19, 28, slope)[..., None]
    col = col + (C["cliff"] - col) * (smoothstep(32, 44, slope) * 0.75)[..., None]
    col = col + (C["shore"] - col) * (1 - smoothstep(2, 10, h))[..., None]
    col = col + (C["bed"] - col) * (1 - smoothstep(-35, 1, h))[..., None]
    if paint:
        def layer(k):
            a = paint.get(k)
            if a is None:
                return None
            return np.clip(ndimage.zoom(a.astype(np.float32), zoom, order=1)[:size, :size], 0, 1)[..., None]
        for k, c in (("concrete", (168, 166, 160)), ("ice", (200, 218, 234)), ("scorch", (58, 44, 38)),
                     ("lava", (90, 34, 18)), ("molten", (255, 140, 30))):
            a = layer(k)
            if a is not None:
                col = col + (np.array(c, np.float32) - col) * a * (0.85 if k == "scorch" else 1.0)
        if paint.get("lava") is not None:          # glowing veins so lava reads as lava
            yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
            veins = (np.abs(np.sin(xx * 0.21 + np.sin(yy * 0.07) * 3) * np.sin(yy * 0.19 + np.sin(xx * 0.05) * 3)) < 0.12)
            col = col + (np.array([255, 120, 30], np.float32) - col) * (veins[..., None] * layer("lava") * 0.8)
    water = h < 0
    if paint and paint.get("lava") is not None:
        water &= np.clip(ndimage.zoom(paint["lava"].astype(np.float32), zoom, order=1)[:size, :size], 0, 1) < 0.5
    col = np.where(water[..., None], col * 0.55 + np.array([20, 60, 110], np.float32) * 0.45, col)
    # hill shading with vertical exaggeration
    ex = 2.2
    nrm = np.stack([-gx * ex, np.ones_like(gx), -gz * ex], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    L = np.array([-0.5, 0.7, -0.5]); L /= np.linalg.norm(L)
    lam = np.clip(nrm @ L, 0, 1)
    ao = np.clip((h - ndimage.gaussian_filter(h, 8)) / 60, -1, 1)
    col = col * (0.5 + 0.7 * lam)[..., None] * (1 + 0.2 * ao)[..., None]
    return np.clip(col, 0, 255).astype(np.uint8)


def preview(design, size=1024, overlays=True):
    """Quick preview image (PIL) of a design: stylised relief, metal spots, geovents, start points,
    template markers and damaging ground outlined in red."""
    img = Image.fromarray(_relief_colors(design.hm, design.biome, design.paint, size))
    if not overlays:
        return img
    d = ImageDraw.Draw(img, "RGBA")
    W = (design.hm.shape[1] - 1) * SQ
    H = (design.hm.shape[0] - 1) * SQ
    sx, sz = size / W, size / H
    if design.hazard is not None and design.hazard.any():
        edge = design.hazard & ~ndimage.binary_erosion(design.hazard, iterations=2)
        e = ndimage.zoom(edge.astype(np.float32), size / (design.hazard.shape[0] - 1), order=0)[:size, :size] > 0.5
        ov = np.zeros((size, size, 4), np.uint8); ov[e] = (255, 60, 30, 200)
        img.alpha_composite(Image.fromarray(ov)) if img.mode == "RGBA" else img.paste(
            Image.fromarray(ov[..., :3]), mask=Image.fromarray(ov[..., 3]))
        d = ImageDraw.Draw(img, "RGBA")
    for m in design.mexes:
        x, z = m["x"] * sx, m["z"] * sz
        r = 3 + m["metal"] * 1.3
        d.ellipse([x - r, z - r, x + r, z + r], outline=(255, 255, 255, 255), fill=(40, 200, 255, 255))
    for g in design.geos:
        x, z = g[0] * sx, g[1] * sz
        d.rectangle([x - 6, z - 6, x + 6, z + 6], outline=(0, 0, 0, 255), fill=(255, 120, 0, 255))
    team_cols = [(60, 255, 60, 255), (255, 70, 70, 255), (90, 160, 255, 255), (255, 220, 60, 255)]
    k = 0
    for ti, team in enumerate(design.teams):
        for p in team:
            c = team_cols[ti % 4]
            x, z = p[0] * sx, p[1] * sz
            d.ellipse([x - 12, z - 12, x + 12, z + 12], outline=(0, 0, 0, 255), width=3, fill=tuple(c))
            k += 1
    for (x, z, label, c) in design.marks:
        x, z = x * sx, z * sz
        d.regular_polygon((x, z, 16), 6, fill=tuple(c), outline=(0, 0, 0))
        d.text((x, z), label, fill=(0, 0, 0), anchor="mm")
    return img


# ----------------------------------------------------------------------------- build
def build(design, outdir=".", config=None, title=None, version=1, name=None, log=print, preview=True):
    """Write the .sdz. Map name = config.map_name(title or design.title, version) unless name is given."""
    cfg = config or ForgeConfig()
    name = name or cfg.map_name(title or design.title, version)
    rng = design.build_rng()
    return build_archive(name, design.hm, design.sym, design.starts, design.mexes, design.geos, design.biome, rng,
                         outdir, cfg.describe(design.description), config=cfg, log=log, preview=preview,
                         extra=dict(template=design.template, seed=design.seed),
                         tree_block=design.tree_block, startboxes=design.startboxes, extra_files=design.extra_files,
                         features=design.features, random_trees=design.random_trees, paint=design.paint,
                         preview_marks=design.marks, preview_start_colors=design.start_colors,
                         keep_clear=design.keep_clear)
