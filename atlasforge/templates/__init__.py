"""Map templates. Each template declares its parameters and turns them into a Design.

    from atlasforge.templates import all_templates, get
    for t in all_templates():
        print(t.id, t.title)
"""
from .arena import Arena
from .base import Param, Template
from .chicken import ChickenRings
from .chokepoint import Chokepoint
from .river import RiverCrossing
from .skirmish import Skirmish
from .volcano import Volcano

_REGISTRY = {t.id: t for t in (Skirmish(), Chokepoint(), RiverCrossing(), Arena(), Volcano(), ChickenRings())}


def all_templates():
    return list(_REGISTRY.values())


def register(template):
    """Add a template at run time (for new templates under development; see docs/TEMPLATE_GUIDE.md)."""
    _REGISTRY[template.id] = template
    return template


def get(template_id):
    try:
        return _REGISTRY[template_id]
    except KeyError:
        raise KeyError(f"unknown template {template_id!r}, expected one of {sorted(_REGISTRY)}") from None


__all__ = ["Param", "Template", "all_templates", "get", "register"]
