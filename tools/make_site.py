"""Write the project website (GitHub Pages, served from the repository root): index.html, sitemap.xml,
robots.txt and .nojekyll. Run after a release or a new template: python tools/make_site.py
The download links point at the newest release tag found in docs/release-notes (vX.Y.Z.md)."""
import datetime
import html
import json
import os
import re

from atlasforge import __version__
from atlasforge.templates import all_templates

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://scuide.github.io/atlas-map-forge/"
REPO = "https://github.com/Scuide/atlas-map-forge"
KOFI = "https://ko-fi.com/scuide"


def newest_tag():
    tags = [f[:-3] for f in os.listdir(os.path.join(ROOT, "docs", "release-notes")) if re.match(r"v\d+\.\d+\.\d+\.md$", f)]
    return max(tags, key=lambda t: tuple(int(x) for x in t[1:].split(".")))


def esc(s):
    return html.escape(str(s), quote=True)


MODE = {"1v1": "1v1", "team": "Teams", "ffa": "FFA", "coop": "Co-op"}


def gallery():
    cards = []
    for t in all_templates():
        tags = [MODE[m] for m in t.modes if m in MODE] + (["Sea"] if "sea" in t.tags else [])
        cards.append(
            f'<li class="tpl"><img src="atlasforge/app/web/thumbs/{t.id}.jpg" alt="{esc(t.title)} map preview" '
            f'width="320" height="320" loading="lazy"><div><h3>{esc(t.title)}</h3><p class="meta">{esc(t.players)}</p>'
            f'<p class="tags">{"".join(f"<span>{esc(x)}</span>" for x in tags)}</p>'
            f'<p class="desc">{esc(t.description)}</p></div></li>')
    return "\n".join(cards)


def page(tag, n_templates):
    ver = tag[1:]
    dl = f"{REPO}/releases/download/{tag}"
    ld = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": "Atlas Map Forge", "applicationCategory": "GameApplication",
        "operatingSystem": "Windows, Linux", "softwareVersion": ver,
        "description": "Free, open-source map generator and map editor for the RTS Zero-K. Builds complete, "
                       "playable Zero-K maps from templates.",
        "url": SITE, "downloadUrl": f"{REPO}/releases/tag/{tag}", "license": "https://www.gnu.org/licenses/gpl-2.0.html",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Person", "name": "Scuide"},
        "screenshot": SITE + "site/img/editor.jpg",
    }
    faq = [
        ("Is Atlas Map Forge free?", "Yes. It is open source under the GPL 2.0 or later, and the Windows and Linux "
         "programs are free downloads."),
        ("Do I need to install anything?", "No. On Windows you start AtlasMapForge.exe; on Linux you unpack the "
         "archive and start ./AtlasMapForge, which opens the app in your web browser. Python is not needed."),
        ("Where do the maps go?", "The Forge finds your Zero-K folder (Steam or the standalone version) and builds the "
         "map straight into its maps folder, so it shows up in the Zero-K lobby right away."),
        ("Can I play generated maps online?", "Yes, in passworded rooms. New maps are \"unsupported\" on zero-k.info "
         "until the Zero-K team approves them."),
        ("Why does Windows warn me?", "The program is not code-signed yet. Click \"More info\", then \"Run anyway\". "
         "Every release is built and tested automatically on GitHub from the public source code."),
        ("Does it make maps for Beyond All Reason?", "Yes, experimental since version 0.6. Pick Beyond All Reason "
         "at the top of the app. BAR takes start boxes from its lobby, so the app shows the !addBox commands for the "
         "host, and size, type and description in BAR's map list stay empty for maps outside BAR's map database."),
        ("Can I change a generated map by hand?", "Yes. The editor shapes terrain, paints paths and scorch marks, "
         "places trees, rocks and wrecks, and moves metal spots, geovents, start points and start boxes. Symmetry "
         "and the reachability checks are kept for every edit."),
    ]
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    faq_html = "\n".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atlas Map Forge: Zero-K map generator and map editor</title>
<meta name="description" content="Free, open-source Zero-K map generator and map editor. Pick one of {n_templates} templates, adjust the settings, edit terrain by hand and build a complete, playable Zero-K map. Windows and Linux.">
<meta name="keywords" content="Zero-K map generator, Zero-K map editor, Zero-K maps, Beyond All Reason map generator, BAR maps, random map generator, Spring RTS map generator, Recoil engine, SpringRTS maps, RTS map maker">
<link rel="canonical" href="{SITE}">
<link rel="icon" href="site/img/favicon.png">
<meta property="og:type" content="website">
<meta property="og:title" content="Atlas Map Forge: Zero-K map generator and map editor">
<meta property="og:description" content="Build complete, playable Zero-K maps from {n_templates} templates and edit them by hand. Free, open source, Windows and Linux.">
<meta property="og:url" content="{SITE}">
<meta property="og:image" content="{SITE}site/img/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld)}</script>
<script type="application/ld+json">{json.dumps(ld_faq)}</script>
<style>
@font-face {{ font-family: "Inter Display"; font-weight: 900; src: url("atlasforge/app/web/InterDisplay-Black.otf") format("opentype"); font-display: swap; }}
:root {{
  --bg: #111215; --panel: #17191d; --panel-2: #1d2025; --line: #2a2e35; --text: #e9e7e3; --muted: #a3a8b0;
  --faint: #6b7079; --ember: #ff7a1a; --ember-hot: #ffb04a; --ok: #5fd38a; --cyan: #46c8ff;
  --ui: "Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif;
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{ margin: 0; background: var(--bg); color: var(--text); font: 16px/1.6 var(--ui); }}
a {{ color: var(--ember-hot); }}
img {{ max-width: 100%; height: auto; display: block; }}
.wrap {{ max-width: 1160px; margin: 0 auto; padding: 0 20px; }}
header.top {{ border-bottom: 1px solid var(--line); background: #0c0d10; }}
header.top .wrap {{ display: flex; align-items: center; gap: 18px; height: 60px; }}
.brand {{ display: flex; align-items: center; gap: 10px; font: 900 18px "Inter Display", var(--ui); letter-spacing: .04em; color: var(--text); text-decoration: none; }}
.brand b {{ color: var(--ember); font-weight: 900; }}
.brand .gem {{ width: 22px; height: 22px; transform: rotate(45deg); border-radius: 4px; background: linear-gradient(135deg, var(--ember-hot), #c2410c); }}
nav {{ margin-left: auto; display: flex; gap: 20px; font-size: 14px; }}
nav a {{ color: var(--muted); text-decoration: none; }}
nav a:hover {{ color: var(--text); }}
.hero {{ padding: 64px 0 40px; background: radial-gradient(1200px 500px at 70% -10%, rgba(255,122,26,.16), transparent 60%); }}
.hero h1 {{ font: 900 clamp(34px, 6vw, 62px)/1.04 "Inter Display", var(--ui); margin: 0 0 14px; letter-spacing: .01em; }}
.hero h1 span {{ display: block; font-size: .5em; color: var(--ember); letter-spacing: .03em; margin-top: 10px; }}
.hero p.lead {{ font-size: clamp(17px, 2.2vw, 20px); color: var(--muted); max-width: 720px; margin: 0 0 28px; }}
.buttons {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
.btn {{ display: inline-flex; align-items: center; gap: 10px; padding: 13px 20px; border-radius: 9px; font-weight: 700; text-decoration: none; border: 1px solid var(--line); color: var(--text); background: var(--panel-2); }}
.btn.primary {{ background: linear-gradient(180deg, #ff9a3c, var(--ember)); color: #1a0d03; border-color: transparent; }}
.btn small {{ font-weight: 500; opacity: .75; }}
.note {{ color: var(--faint); font-size: 14px; margin-top: 14px; }}
.shot {{ margin-top: 40px; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; box-shadow: 0 30px 80px rgba(0,0,0,.5); }}
section {{ padding: 56px 0; border-top: 1px solid var(--line); }}
h2 {{ font: 900 clamp(26px, 3.6vw, 36px)/1.15 "Inter Display", var(--ui); margin: 0 0 10px; letter-spacing: .01em; }}
.sub {{ color: var(--muted); margin: 0 0 30px; max-width: 760px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; }}
.card h3 {{ margin: 0 0 6px; font-size: 17px; }}
.card p {{ margin: 0; color: var(--muted); font-size: 15px; }}
.steps {{ counter-reset: s; list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
.steps li {{ counter-increment: s; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px 18px 64px; position: relative; color: var(--muted); }}
.steps li::before {{ content: counter(s); position: absolute; left: 20px; top: 16px; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; color: #1a0d03; background: var(--ember); }}
.steps b {{ color: var(--text); display: block; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.two figure {{ margin: 0; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; background: var(--panel); }}
.two figcaption {{ padding: 10px 14px; color: var(--muted); font-size: 14px; }}
.tpls {{ list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }}
.tpl {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
.tpl img {{ width: 100%; aspect-ratio: 1; object-fit: cover; }}
.tpl div {{ padding: 10px 12px 12px; }}
.tpl h3 {{ margin: 0; font-size: 15px; }}
.tpl .meta {{ margin: 2px 0 6px; color: var(--faint); font-size: 13px; }}
.tpl .tags {{ margin: 0 0 6px; display: flex; flex-wrap: wrap; gap: 4px; }}
.tpl .tags span {{ font-size: 11px; padding: 1px 7px; border-radius: 5px; background: var(--panel-2); border: 1px solid var(--line); color: var(--muted); }}
.tpl .desc {{ margin: 0; font-size: 13px; color: var(--muted); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
details {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }}
summary {{ cursor: pointer; font-weight: 700; }}
details p {{ color: var(--muted); margin: 10px 0 0; }}
footer {{ border-top: 1px solid var(--line); padding: 28px 0 40px; color: var(--faint); font-size: 14px; }}
footer .wrap {{ display: flex; flex-wrap: wrap; gap: 18px; justify-content: space-between; }}
@media (max-width: 760px) {{
  nav {{ display: none; }}
  .two {{ grid-template-columns: 1fr; }}
  .hero {{ padding-top: 40px; }}
}}
</style>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="./"><span class="gem"></span>ATLAS MAP <b>FORGE</b></a>
  <nav><a href="#features">Features</a><a href="#editor">Editor</a><a href="#templates">Templates</a><a href="#faq">FAQ</a><a href="{REPO}">GitHub</a></nav>
</div></header>

<main>
<div class="hero"><div class="wrap">
  <h1>Atlas Map Forge<span>Zero-K map generator and map editor</span></h1>
  <p class="lead">Build complete, playable maps for the RTS <a href="https://zero-k.info">Zero-K</a> in minutes: pick one of {n_templates} templates, adjust the settings, shape the terrain by hand and press Build. The map lands in your Zero-K maps folder, ready to play.</p>
  <div class="buttons">
    <a class="btn primary" href="{dl}/AtlasMapForge.exe">Download for Windows <small>v{ver} &middot; .exe</small></a>
    <a class="btn" href="{dl}/AtlasMapForge-linux-x86_64.tar.gz">Linux <small>.tar.gz</small></a>
    <a class="btn" href="{REPO}">Source on GitHub</a>
  </div>
  <p class="note">Free and open source (GPL 2.0 or later). One file, no installation, no Python needed. Pre-release: feedback is welcome.</p>
  <div class="shot"><img src="site/img/editor.jpg" width="1600" height="960" alt="Atlas Map Forge app: a Zero-K map in the editor with metal spots, start boxes, chokes and the check report"></div>
</div></div>

<section id="features"><div class="wrap">
  <h2>What it does</h2>
  <p class="sub">A complete map, not just a heightmap: texture, minimap, metal spots, geothermal vents, start boxes, trees and optional map gadgets, packed as a ready-to-play .sdz file.</p>
  <div class="grid">
    <div class="card"><h3>{n_templates} templates</h3><p>Land, sea, chokepoints, rivers, islands, free-for-all for 3 to 8 players, co-op chicken defence, a volcano with eruptions and an asteroid in space.</p></div>
    <div class="card"><h3>Fair by design</h3><p>Terrain, metal and start boxes are mirrored or rotated, so every side gets exactly the same.</p></div>
    <div class="card"><h3>Checked like the engine</h3><p>A report shows whether tanks, bots, spiders, hovers, amphibians and ships can reach the enemy and every metal spot, using the engine's own slope rules.</p></div>
    <div class="card"><h3>12 biomes</h3><p>Temperate, autumn, desert, arctic, jungle, swamp, industrial, alien, moon, volcanic, ashland and asteroid, each with its own sky, light and grass.</p></div>
    <div class="card"><h3>Every setting explained</h3><p>Size, seed, time of day, metal, geovents, wind, tidal strength, trees, rocks, wrecks, erosion and each template's own options, with a short explanation for each.</p></div>
    <div class="card"><h3>Beyond All Reason too</h3><p>Switch "Map for" to Beyond All Reason (experimental): metal, wrecks, lava and the reachability checks follow BAR's rules, and the map is installed into BAR.</p></div>
    <div class="card"><h3>Straight into the game</h3><p>The Zero-K folder is found automatically; the built map shows up in the Zero-K lobby.</p></div>
  </div>
</div></section>

<section><div class="wrap">
  <h2>How it works</h2>
  <ol class="steps">
    <li><b>Pick a template</b>Filter by 1v1, teams, free-for-all, co-op, land or sea.</li>
    <li><b>Adjust and edit</b>Change the settings or roll a new seed; refine the map by hand in the editor.</li>
    <li><b>Build and play</b>One click builds the .sdz map into your Zero-K maps folder.</li>
  </ol>
</div></section>

<section id="editor"><div class="wrap">
  <h2>A map editor built in</h2>
  <p class="sub">Change a generated map before you build it. Every edit follows the map's symmetry and the checks run again after each one. Undo, redo and project files (.forge.json) included.</p>
  <div class="two">
    <figure><img src="site/img/3d.jpg" width="938" height="690" loading="lazy" alt="3D terrain view of a Zero-K river delta map in Atlas Map Forge"><figcaption>3D view: rotate and zoom the terrain with metal spots and start points.</figcaption></figure>
    <figure><img src="site/img/slope.jpg" width="938" height="690" loading="lazy" alt="Slope overlay showing where Zero-K units can drive and climb"><figcaption>Slope map: where all units, only bots and spiders, or nothing can go.</figcaption></figure>
  </div>
  <div class="grid" style="margin-top:16px">
    <div class="card"><h3>Terrain</h3><p>Raise, lower, flatten to a height, smooth, roughen and terrace; ramps from A to B; a stamp that copies terrain, turned or mirrored.</p></div>
    <div class="card"><h3>Paint</h3><p>Paths, concrete, scorch marks and lava crust, with an eraser, polygon fill and height-band fill.</p></div>
    <div class="card"><h3>Objects</h3><p>Move metal spots, geovents, start points and start boxes, also several at once; add or remove trees, rocks and wrecks.</p></div>
    <div class="card"><h3>Overview</h3><p>Live metal balance per team, an edit list with on and off per edit, contour lines and zoom up to 8x.</p></div>
  </div>
</div></section>

<section id="templates"><div class="wrap">
  <h2>{n_templates} map templates</h2>
  <p class="sub">Every template has its own settings, and every seed gives a different map.</p>
  <ul class="tpls">
{gallery()}
  </ul>
</div></section>

<section id="faq"><div class="wrap">
  <h2>Questions</h2>
  {faq_html}
</div></section>
</main>

<footer><div class="wrap">
  <span>Atlas Map Forge v{ver} &middot; made by Scuide (Ling Ling in game) &middot; not affiliated with the Zero-K team</span>
  <span><a href="{REPO}">GitHub</a> &middot; <a href="{REPO}/issues">Report a problem</a> &middot; <a href="{REPO}/blob/main/CHANGELOG.md">Changelog</a> &middot; <a href="{KOFI}">Support on Ko-fi</a></span>
</div></footer>
</body>
</html>
"""


def main():
    tag = newest_tag()
    n = len(all_templates())
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(tag, n))
    today = datetime.date.today().isoformat()
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f"  <url><loc>{SITE}</loc><lastmod>{today}</lastmod></url>\n</urlset>\n")
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
    open(os.path.join(ROOT, ".nojekyll"), "w").close()
    print(f"site for {tag} (app {__version__}), {n} templates")


if __name__ == "__main__":
    main()
