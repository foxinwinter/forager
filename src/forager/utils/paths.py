from __future__ import annotations
from pathlib import Path

from forager.core.config import default_cache_dir, settings


def cache_dir() -> Path:
    return default_cache_dir()


def art_cache_dir() -> Path:
    p = cache_dir() / "art"
    p.mkdir(parents=True, exist_ok=True)
    return p


def icon_cache_dir() -> Path:
    p = cache_dir() / "icons"
    p.mkdir(parents=True, exist_ok=True)
    return p


def banner_cache_dir() -> Path:
    p = cache_dir() / "banners"
    p.mkdir(parents=True, exist_ok=True)
    return p


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
