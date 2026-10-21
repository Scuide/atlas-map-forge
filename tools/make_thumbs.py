"""Render the template gallery pictures for the app (atlasforge/app/web/thumbs/<id>.jpg).
Run after changing a template: python tools/make_thumbs.py"""
import os

from atlasforge import forge
from atlasforge.templates import all_templates

OUT = os.path.join(os.path.dirname(__file__), "..", "atlasforge", "app", "web", "thumbs")
os.makedirs(OUT, exist_ok=True)
for t in all_templates():
    d = forge.make(t.id, {}, seed=7, log=lambda *a: None)
    forge.preview(d, size=720).resize((320, 320)).convert("RGB").save(os.path.join(OUT, t.id + ".jpg"), quality=86)
    print(t.id)
