"""Editor SCU-75: zoom / pan / coordinate maths of the preview (view.js), run with node."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_view_math_js():
    r = subprocess.run(["node", str(ROOT / "tests" / "view_math.test.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_view_js_is_loaded_before_app():
    html = (ROOT / "atlasforge" / "app" / "web" / "index.html").read_text(encoding="utf-8")
    assert html.index("view.js") < html.index("app.js")
