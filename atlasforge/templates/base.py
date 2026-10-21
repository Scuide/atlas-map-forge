"""Template interface.

A template turns a few parameters into a Design (heightmap, resources, start boxes, paint layers, map
gadgets). Parameters are declared with type, range, default and help text so a user interface can build
its controls automatically.
"""
from dataclasses import dataclass
from typing import Any, Optional

from ..design import Design  # noqa: F401  (re-export)


@dataclass
class Param:
    key: str
    label: str
    kind: str                       # "int", "float", "choice", "bool"
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[tuple] = None
    help: str = ""

    def coerce(self, v):
        if self.kind == "bool":
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "on")
            return bool(v)
        if self.kind == "choice":
            vals = [str(c) for c in self.choices]
            if str(v) not in vals:
                raise ValueError(f"{self.key}: {v!r} is not one of {vals}")
            return self.choices[vals.index(str(v))]
        if self.kind == "int":
            v = int(round(float(v)))
        elif self.kind == "float":
            v = float(v)
        else:
            raise ValueError(f"unknown parameter kind {self.kind}")
        if self.min is not None and v < self.min or self.max is not None and v > self.max:
            raise ValueError(f"{self.key}: {v} is outside {self.min}..{self.max}")
        return v

    def to_dict(self):
        d = {k: getattr(self, k) for k in ("key", "label", "kind", "default", "min", "max", "step", "help")}
        if self.choices is not None:
            d["choices"] = list(self.choices)
        return d


class Template:
    id = ""
    title = ""
    description = ""
    params = ()

    def param(self, key):
        for p in self.params:
            if p.key == key:
                return p
        raise KeyError(key)

    def defaults(self):
        return {p.key: p.default for p in self.params}

    def resolve(self, values=None):
        """Defaults + given values, checked and converted. Unknown keys raise an error."""
        out = self.defaults()
        for k, v in (values or {}).items():
            out[k] = self.param(k).coerce(v)
        return out

    def make(self, values, seed, log=print):
        """-> Design. values: resolved parameter dict."""
        raise NotImplementedError

    def info(self):
        return dict(id=self.id, title=self.title, description=self.description,
                    params=[p.to_dict() for p in self.params])
