"""Art loading for games: header / grid / hero / logo images.

Resolution order (per image): local Steam appcache art (Steam games), the on
disk art cache, the Steam CDN for the resolved ``app_id``, SteamGridDB by app
id, SteamGridDB by search, then the generated placeholders.
"""
from __future__ import annotations
import hashlib
import urllib.request
from pathlib import Path
from PySide6.QtGui import QPixmap

from forager.core.game import Game, Source
from forager.library.icon_provider import load_icon
from forager.library.steamgriddb import (
    fetch_header_bytes_for_steam,
    fetch_banner_bytes_for_steam,
    fetch_grid_bytes_for_steam, fetch_grid_bytes_for_game,
    fetch_header_bytes_for_game,
    fetch_banner_bytes_for_game,
)
from forager.services.pixmap_utils import bytes_to_pixmap, scale_crop, scaled
from forager.services.placeholder import (
    placeholder_card,
    placeholder_grid,
    register_placeholder_font,
)
from forager.services.steam_app_id import steam_app_id
from forager.utils.paths import art_cache_dir, banner_cache_dir, steam_appcache_dir

STEAM_CACHE = steam_appcache_dir()
ART_CACHE = art_cache_dir()
BANNER_CACHE = banner_cache_dir()
STEAM_CDN = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{app_id}/{name}"


def _ensure_cache():
    ART_CACHE.mkdir(parents=True, exist_ok=True)


def _cache_key(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:16]


def _steam_path(game: Game, filename: str) -> Path | None:
    if game.source != Source.STEAM or not game.app_id:
        return None
    p = STEAM_CACHE / game.app_id / filename
    return p if p.is_file() else None


# -- Steam CDN ----------------------------------------------------------

def _steam_cdn_bytes(app_id: str, names: tuple[str, ...]) -> bytes | None:
    for name in names:
        url = STEAM_CDN.format(app_id=app_id, name=name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "forager/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except Exception:
            continue
    return None


def _steam_cdn_grid_bytes(app_id: str) -> bytes | None:
    return _steam_cdn_bytes(app_id, ("library_600x900.jpg", "library_600x900_2x.jpg"))


# -- on-disk caches -----------------------------------------------------

def _image_ext(data: bytes) -> str:
    return ".jpg" if data[:3] == b"\xff\xd8" else ".png"


def _cached_path(dir_: Path, prefix: str, key: str) -> Path | None:
    for ext in (".jpg", ".png"):
        p = dir_ / f"{prefix}_{key}{ext}"
        if p.is_file():
            return p
    return None


def _cached_header_path(game: Game) -> Path | None:
    _ensure_cache()
    return _cached_path(ART_CACHE, "header", _cache_key(game.app_id or game.name))


def _cached_grid_path(game: Game) -> Path | None:
    _ensure_cache()
    return _cached_path(ART_CACHE, "grid", _cache_key(game.app_id or game.name))


def _cached_hero_path(game: Game) -> Path | None:
    BANNER_CACHE.mkdir(parents=True, exist_ok=True)
    return _cached_path(BANNER_CACHE, "hero", _cache_key(game.app_id or game.name))


# -- header -------------------------------------------------------------

def load_header_bytes(game: Game, allow_network: bool = True) -> bytes | None:
    local = _steam_path(game, "header.jpg")
    if local is not None:
        return local.read_bytes()

    cached = _cached_header_path(game)
    if cached is not None:
        return cached.read_bytes()

    if not allow_network:
        return None

    data = None
    app_id = steam_app_id(game)
    if app_id:
        data = _steam_cdn_bytes(app_id, ("header.jpg",))
    if data is None and app_id:
        data = fetch_header_bytes_for_steam(app_id)
    if data is None:
        data = fetch_header_bytes_for_game(game)
    if data:
        _ensure_cache()
        key = _cache_key(game.app_id or game.name)
        (ART_CACHE / f"header_{key}.png").write_bytes(data)
    return data


def load_header(game: Game, allow_network: bool = True) -> QPixmap | None:
    data = load_header_bytes(game, allow_network)
    return bytes_to_pixmap(data) if data else None


# -- grid ---------------------------------------------------------------

def load_grid_bytes(game: Game, allow_network: bool = True) -> bytes | None:
    if game.source == Source.STEAM and game.app_id:
        for name in ("library_600x900.jpg", "header.jpg"):
            local = _steam_path(game, name)
            if local is not None:
                return local.read_bytes()

    cached = _cached_grid_path(game)
    if cached is not None:
        return cached.read_bytes()

    if not allow_network:
        return None

    data = None
    app_id = steam_app_id(game)
    if app_id:
        data = _steam_cdn_grid_bytes(app_id)
    if data is None and app_id:
        data = fetch_grid_bytes_for_steam(app_id)
    if data is None:
        data = fetch_grid_bytes_for_game(game)
    if data:
        _ensure_cache()
        key = _cache_key(game.app_id or game.name)
        (ART_CACHE / f"grid_{key}{_image_ext(data)}").write_bytes(data)
    return data


def load_grid(game: Game, allow_network: bool = True) -> QPixmap | None:
    data = load_grid_bytes(game, allow_network)
    return bytes_to_pixmap(data) if data else None


# -- hero ---------------------------------------------------------------

def load_hero_bytes(game: Game, allow_network: bool = True) -> bytes | None:
    for name in ("library_hero.jpg", "library_hero_blur.jpg"):
        local = _steam_path(game, name)
        if local is not None:
            return local.read_bytes()

    cached = _cached_hero_path(game)
    if cached is not None:
        return cached.read_bytes()

    if not allow_network:
        return None

    data = None
    app_id = steam_app_id(game)
    if app_id:
        data = _steam_cdn_bytes(app_id, ("library_hero.jpg", "library_hero_blur.jpg"))
    if data is None and app_id:
        data = fetch_banner_bytes_for_steam(app_id)
    if data is None:
        data = fetch_banner_bytes_for_game(game)
    if data:
        BANNER_CACHE.mkdir(parents=True, exist_ok=True)
        key = _cache_key(game.app_id or game.name)
        (BANNER_CACHE / f"hero_{key}{_image_ext(data)}").write_bytes(data)
        return data
    return load_header_bytes(game, allow_network)


def load_hero(game: Game, allow_network: bool = True) -> QPixmap | None:
    for name in ("library_hero.jpg", "library_hero_blur.jpg", "header.jpg"):
        local = _steam_path(game, name)
        if local is not None:
            pix = QPixmap(str(local))
            if not pix.isNull():
                return pix
    cached = _cached_hero_path(game)
    if cached is not None:
        pix = QPixmap(str(cached))
        if not pix.isNull():
            return pix
    data = load_hero_bytes(game, allow_network)
    return bytes_to_pixmap(data) if data else None


# -- logo ---------------------------------------------------------------

def load_logo(game: Game) -> QPixmap | None:
    local = _steam_path(game, "logo.png")
    if local is not None:
        pix = QPixmap(str(local))
        if not pix.isNull():
            return pix
    return None
