"""SCU-84: the help table in app.js (TOOL_HELP) covers every editor tool of the toolbar and feeds its tooltips."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "atlasforge" / "app" / "web"


def _help_tools():
    src = (WEB / "app.js").read_text(encoding="utf-8")
    table = src[src.index("const TOOL_HELP = ["):src.index("const OTHER_KEYS")]
    return re.findall(r'tool: "(\w+)", name: "[^"]+", keys: "[^"]+", desc: "[^"]+"', table)


def test_help_table_lists_every_toolbar_tool():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    toolbar = set(re.findall(r'data-tool="(\w+)"', html))
    assert toolbar, "no tool buttons found"
    tools = _help_tools()
    assert len(tools) == len(set(tools))
    assert set(tools) == toolbar


def test_tool_buttons_get_their_tooltip_from_the_table():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert not re.search(r'<button data-tool="\w+"[^>]*title=', html)
    assert 'id="btn-help"' in html and 'id="help"' in html
