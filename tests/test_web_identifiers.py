"""Regression: every ed*() call in the web JS must have a definition (SCU-87: edIsTreeTool was renamed but still called)."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "atlasforge" / "app" / "web"


def _strip(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def test_called_ed_functions_are_defined():
    srcs = {p.name: _strip(p.read_text(encoding="utf-8")) for p in WEB.glob("*.js")}
    alltext = "\n".join(srcs.values())
    defined = set(re.findall(r"\b(?:function\s+|const\s+|let\s+|var\s+)(ed[A-Z]\w*)", alltext))
    defined |= set(re.findall(r"\b(?:async\s+function\s+)(ed[A-Z]\w*)", alltext))
    called = {}
    for name, src in srcs.items():
        for m in re.finditer(r"(?<![\w.$])(ed[A-Z]\w*)\s*\(", src):
            called.setdefault(m.group(1), name)
    missing = {k: v for k, v in called.items() if k not in defined}
    assert not missing, f"called but never defined: {missing}"
