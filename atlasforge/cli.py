"""Command line: atlasforge <command> ...

  atlasforge procedural --title "Ashfall Ridge" --size 12 12 --biome volcanic --style plateaus --seed 7
  atlasforge config --author "MyName" --prefix "Forge"
  atlasforge find-zerok
  atlasforge install path/to/map.sdz [--zerok DIR]
"""
import argparse
import json
import sys

from . import __version__
from . import config as C


def _cmd_procedural(a):
    from .procedural import STYLES, LAYOUTS, generate   # noqa: F401
    cfg = C.load()
    if a.author:
        cfg.author = a.author
    if a.prefix is not None:
        cfg.prefix = a.prefix
    if a.badge:
        cfg.badge = a.badge
    cfg.validate()
    info = generate(a.title, tuple(a.size), a.seed, a.biome, a.style, a.layout, a.relief, a.out, cfg,
                    version=a.version, mex_per_side=a.mex, preview=not a.no_preview)
    if a.install is not None:
        from .install import find_zerok, install
        target = a.install or (find_zerok() or [None])[0]
        if not target:
            print("Zero-K folder not found, use --install <folder>", file=sys.stderr)
            return 2
        install(info["path"], target)
    print(json.dumps(info, indent=1))
    return 0


def _cmd_config(a):
    cfg = C.load()
    changed = False
    for k in ("author", "prefix", "badge"):
        v = getattr(a, k)
        if v is not None:
            setattr(cfg, k, v); changed = True
    if a.no_credit:
        cfg.credit = False; changed = True
    if changed:
        print("saved", C.save(cfg))
    print(json.dumps(cfg.__dict__, indent=1))
    return 0


def _cmd_find(a):
    from .install import find_zerok
    found = find_zerok()
    print("\n".join(found) if found else "Zero-K folder not found")
    return 0 if found else 1


def _cmd_install(a):
    from .install import find_zerok, install
    target = a.zerok or (find_zerok() or [None])[0]
    if not target:
        print("Zero-K folder not found, use --zerok <folder>", file=sys.stderr)
        return 2
    for p in a.maps:
        install(p, target)
    return 0


def main(argv=None):
    import multiprocessing
    multiprocessing.freeze_support()          # needed for frozen Windows builds (PyInstaller)
    from .biomes import BIOMES
    from .procedural import LAYOUTS, STYLES
    ap = argparse.ArgumentParser(prog="atlasforge", description="Atlas Map Forge - map generator for Zero-K")
    ap.add_argument("--version", action="version", version=f"Atlas Map Forge {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("procedural", help="build a procedural skirmish map")
    p.add_argument("--title", required=True, help="map title; the name becomes '<prefix> <title> v<version>'")
    p.add_argument("--version", dest="version", type=int, default=1, help="map version number (default 1)")
    p.add_argument("--size", nargs=2, type=int, default=[12, 12], metavar=("W", "H"),
                   help="map size in Spring units, even numbers 4..32 (default 12 12)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--biome", choices=sorted(BIOMES), default="temperate")
    p.add_argument("--style", choices=STYLES, default="hills")
    p.add_argument("--layout", choices=LAYOUTS, default="diag",
                   help="team symmetry: diag (NW vs SE), ns (north vs south), ew (west vs east)")
    p.add_argument("--relief", type=float, default=None, help="height scale (1.0 = default)")
    p.add_argument("--mex", type=int, default=None, help="metal spots per side")
    p.add_argument("--out", default=".", help="output folder")
    p.add_argument("--author"); p.add_argument("--prefix"); p.add_argument("--badge", choices=C.BADGES)
    p.add_argument("--no-preview", action="store_true")
    p.add_argument("--install", nargs="?", const="", default=None, metavar="ZEROK_DIR",
                   help="install into Zero-K after building (folder optional, found automatically)")
    p.set_defaults(func=_cmd_procedural)

    p = sub.add_parser("config", help="show or change the saved settings")
    p.add_argument("--author"); p.add_argument("--prefix"); p.add_argument("--badge", choices=C.BADGES)
    p.add_argument("--no-credit", action="store_true", help="do not append 'Made with Atlas Map Forge'")
    p.set_defaults(func=_cmd_config)

    p = sub.add_parser("find-zerok", help="show the Zero-K folders that were found")
    p.set_defaults(func=_cmd_find)

    p = sub.add_parser("install", help="install built maps into Zero-K")
    p.add_argument("maps", nargs="+")
    p.add_argument("--zerok", help="Zero-K folder (found automatically if omitted)")
    p.set_defaults(func=_cmd_install)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
