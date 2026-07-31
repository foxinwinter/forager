from __future__ import annotations
import json
import os
from pathlib import Path

APP_NAME = "forager"

DEFAULTS = {
    "games_dir": str(Path.home() / "Games"),
    "steam_appcache": str(Path.home() / ".local/share/Steam/appcache/librarycache"),
    "proton": {
        "prefix_name": "single",
        "features": {
            "rpgmaker_vxace_rtp": False,
        },
    },
}


def default_config_dir() -> Path:
    override = os.getenv("FORAGER_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".config" / APP_NAME


def default_cache_dir() -> Path:
    override = os.getenv("FORAGER_CACHE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / APP_NAME


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_config_dir() / "settings.json"
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        data: dict = {}
        try:
            if self.path.is_file():
                raw = json.loads(self.path.read_text("utf-8"))
                if isinstance(raw, dict):
                    data = raw
        except (OSError, json.JSONDecodeError):
            data = {}
        self._data = _deep_merge(DEFAULTS, data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2) + "\n", "utf-8")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    @property
    def data(self) -> dict:
        return self._data

    @property
    def games_dir(self) -> Path:
        return Path(str(self._data.get("games_dir") or DEFAULTS["games_dir"])).expanduser()

    @property
    def steam_appcache(self) -> Path:
        return Path(str(self._data.get("steam_appcache") or DEFAULTS["steam_appcache"])).expanduser()

    @property
    def proton_prefix_name(self) -> str:
        return str(self._data.get("proton", {}).get("prefix_name") or "single")

    @property
    def proton_features(self) -> dict:
        return self._data.get("proton", {}).get("features", {})

    def proton_feature(self, name: str) -> bool:
        return bool(self.proton_features.get(name, False))


settings = Settings()
