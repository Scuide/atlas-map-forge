"""User settings (author, name prefix, badge) and per-user folders.

Settings are stored as JSON:
  Windows: %APPDATA%\\AtlasMapForge\\config.json
  other:   ~/.config/atlas-map-forge/config.json
"""
import json
import os
import sys
from dataclasses import asdict, dataclass

TOOL_NAME = "Atlas Map Forge"
BADGES = ("forge", "none")


def _config_dir():
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AtlasMapForge")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "atlas-map-forge")


def cache_dir():
    """Folder for cached detail materials (shared by all maps)."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "AtlasMapForge", "cache")
    return os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "atlas-map-forge")


@dataclass
class ForgeConfig:
    author: str = "Unknown"          # shown on the map page (mapinfo author)
    prefix: str = "Forge"            # map names become "<prefix> <title> v<version>"; empty = no prefix
    badge: str = "forge"             # minimap badge in the map browser: "forge" or "none"
    credit: bool = True              # append "Made with Atlas Map Forge." to the description

    def map_name(self, title, version=1):
        base = f"{self.prefix} {title}".strip() if self.prefix else title
        return f"{base} v{version}"

    def describe(self, text):
        return f"{text} Made with {TOOL_NAME}." if self.credit else text

    def validate(self):
        if self.badge not in BADGES:
            raise ValueError(f"badge must be one of {BADGES}, got {self.badge!r}")
        for field in ("author", "prefix"):
            v = getattr(self, field)
            if any(c in v for c in '"\\\n'):
                raise ValueError(f"{field} must not contain quotes, backslashes or line breaks")
        return self


def config_path():
    return os.path.join(_config_dir(), "config.json")


def load():
    p = config_path()
    if os.path.exists(p):
        with open(p, encoding="utf8") as f:
            data = json.load(f)
        known = {k: v for k, v in data.items() if k in ForgeConfig.__dataclass_fields__}
        return ForgeConfig(**known).validate()
    return ForgeConfig()


def save(cfg):
    cfg.validate()
    os.makedirs(_config_dir(), exist_ok=True)
    with open(config_path(), "w", encoding="utf8") as f:
        json.dump(asdict(cfg), f, indent=2)
    return config_path()
