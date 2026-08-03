"""Artwork cache directory management.

The on-disk art caches live under the user's cache directory (see
``forager.core.config.default_cache_dir``) in ``art/`` (headers, grids,
heroes), ``banners/`` (game-page hero banners) and ``icons/`` (tile icons).
Every directory is created on demand.
"""
from __future__ import annotations
from pathlib import Path

from forager.core.config import default_cache_dir
from forager.utils.filesystem import ensure_dir


def cache_dir() -> Path:
    return default_cache_dir()


def art_cache_dir() -> Path:
    return ensure_dir(cache_dir() / "art")


def icon_cache_dir() -> Path:
    return ensure_dir(cache_dir() / "icons")


def banner_cache_dir() -> Path:
    return ensure_dir(cache_dir() / "banners")
