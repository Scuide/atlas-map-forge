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
    adv_min: Optional[float] = None  # wider limits in advanced mode (may give unplayable or broken maps)
    adv_max: Optional[float] = None
    adv_choices: Optional[tuple] = None
    group: str = ""                  # heading in the app ("" = template settings)

    def limits(self, advanced=False):
        lo, hi = self.min, self.max
        if advanced:
            lo = self.adv_min if self.adv_min is not None else lo
            hi = self.adv_max if self.adv_max is not None else hi
        return lo, hi

    def options(self, advanced=False):
        return self.adv_choices if advanced and self.adv_choices else self.choices

    def coerce(self, v, advanced=False):
        if self.kind == "bool":
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "on")
            return bool(v)
        if self.kind == "choice":
            opts = self.options(advanced)
            vals = [str(c) for c in opts]
            if str(v) not in vals:
                more = " (more in advanced mode)" if not advanced and self.adv_choices else ""
                raise ValueError(f"{self.key}: {v!r} is not one of {vals}{more}")
            return opts[vals.index(str(v))]
        if self.kind == "int":
            v = int(round(float(v)))
        elif self.kind == "float":
            v = float(v)
        else:
            raise ValueError(f"unknown parameter kind {self.kind}")
        lo, hi = self.limits(advanced)
        if lo is not None and v < lo or hi is not None and v > hi:
            more = " (wider limits in advanced mode)" if not advanced and (self.adv_min is not None
                                                                          or self.adv_max is not None) else ""
            raise ValueError(f"{self.key}: {v} is outside {lo:g}..{hi:g}{more}")
        return v

    def to_dict(self):
        d = {k: getattr(self, k) for k in ("key", "label", "kind", "default", "min", "max", "step", "help",
                                           "adv_min", "adv_max", "group")}
        if self.choices is not None:
            d["choices"] = list(self.choices)
        if self.adv_choices is not None:
            d["adv_choices"] = list(self.adv_choices)
        return d


class Template:
    id = ""
    title = ""
    description = ""
    params = ()

    def all_params(self):
        """Template parameters followed by the general ones every template has."""
        from .common import general_params
        return tuple(self.params) + general_params()

    def param(self, key):
        for p in self.all_params():
            if p.key == key:
                return p
        raise KeyError(key)

    def defaults(self):
        return {p.key: p.default for p in self.all_params()}

    def resolve(self, values=None, advanced=False):
        """Defaults + given values, checked and converted. Unknown keys raise an error.
        advanced: allow the wider advanced-mode limits."""
        out = self.defaults()
        for k, v in (values or {}).items():
            out[k] = self.param(k).coerce(v, advanced)
        return out

    def make(self, values, seed, log=print):
        """-> Design. values: resolved parameter dict."""
        raise NotImplementedError

    def info(self):
        return dict(id=self.id, title=self.title, description=self.description,
                    params=[p.to_dict() for p in self.all_params()])
