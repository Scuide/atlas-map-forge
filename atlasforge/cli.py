"""Command line: atlasforge <command> ...

  atlasforge templates                                   list templates and their parameters
  atlasforge preview chokepoint --set gates=4 --seed 3   quick preview image + check report
  atlasforge build volcano --set bomb_rate=1.2 --title "Ember Atoll" --install
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


def _parse_sets(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--set expects key=value, got {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _cmd_templates(a):
    from .templates import all_templates
    for t in all_templates():
        print(f"{t.id:11s} {t.title}")
        print(f"            {t.description}")
        for p in t.params:
            rng = f"{p.min:g}..{p.max:g}" if p.min is not None else (" | ".join(map(str, p.choices)) if p.choices else "on/off")
            print(f"            --set {p.key}=...  {p.label} (default {p.default}; {rng})")
        print()
    return 0


def _design_from_args(a):
    from . import forge
    return forge.make(a.template, _parse_sets(a.set), seed=a.seed)


def _print_report(d):
    from . import forge
    ok, lines = forge.check(d)
    print("Check:", "OK" if ok else "PROBLEMS FOUND")
    for line in lines:
        print("  " + line)
    return ok


def _cmd_preview(a):
    from . import forge
    d = _design_from_args(a)
    ok = _print_report(d)
    out = a.out or f"{a.template}_{a.seed}_preview.png"
    forge.preview(d, size=a.size).save(out)
    print("preview:", out)
    return 0 if ok else 1


def _cmd_build(a):
    from . import forge
    cfg = C.load()
    if a.author:
        cfg.author = a.author
    if a.prefix is not None:
        cfg.prefix = a.prefix
    if a.badge:
        cfg.badge = a.badge
    cfg.validate()
    d = _design_from_args(a)
    ok = _print_report(d)
    if not ok and not a.force:
        print("Not built because the check found problems (use --force to build anyway).", file=sys.stderr)
        return 1
    info = forge.build(d, outdir=a.out, config=cfg, title=a.title, version=a.version)
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

    p = sub.add_parser("templates", help="list map templates and their parameters")
    p.set_defaults(func=_cmd_templates)

    from .templates import all_templates
    ids = [t.id for t in all_templates()]
    for cmd, helptext in (("preview", "quick preview image and check report"), ("build", "build a map from a template")):
        p = sub.add_parser(cmd, help=helptext)
        p.add_argument("template", choices=ids)
        p.add_argument("--set", action="append", metavar="KEY=VALUE", help="template parameter (repeatable)")
        p.add_argument("--seed", type=int, default=1)
        if cmd == "preview":
            p.add_argument("--out", help="image file (default <template>_<seed>_preview.png)")
            p.add_argument("--size", type=int, default=1024, help="image size in pixels")
            p.set_defaults(func=_cmd_preview)
        else:
            p.add_argument("--title", help="map title (default: the template's title)")
            p.add_argument("--version", dest="version", type=int, default=1)
            p.add_argument("--out", default=".")
            p.add_argument("--author"); p.add_argument("--prefix"); p.add_argument("--badge", choices=C.BADGES)
            p.add_argument("--force", action="store_true", help="build even if the check finds problems")
            p.add_argument("--install", nargs="?", const="", default=None, metavar="ZEROK_DIR")
            p.set_defaults(func=_cmd_build)

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
