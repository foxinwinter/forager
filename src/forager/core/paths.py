from __future__ import annotations
from pathlib import Path

from forager.core.config import default_config_dir, settings
from forager.core.constants import ASSETS_DIRNAME


def resources_dir() -> Path:
    """Path to the packaged assets directory (icons, fonts).

    Resolved from the installed package location, so it works identically
    from a source checkout (``PYTHONPATH=src``) and from an installed wheel.
    """
    from importlib import resources

    return Path(str(resources.files("forager") / ASSETS_DIRNAME))



def games_dir() -> Path:
    return settings.games_dir


def steam_appcache_dir() -> Path:
    return settings.steam_appcache


def steam_client_dir() -> Path:
    return steam_appcache_dir().parent.parent


def runtime_dir() -> Path:
    return games_dir() / ".runtime"


def proton_dir() -> Path:
    return runtime_dir() / "proton"


def proton_prefix_dir() -> Path:
    return proton_dir() / "files"


def rtp_source_dir() -> Path:
    return runtime_dir() / "rtp"


def playtime_file() -> Path:
    return default_config_dir() / "playtime.json"
