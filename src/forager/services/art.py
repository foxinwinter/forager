from __future__ import annotations
import hashlib
import io
import json
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QFontMetrics
from forager.core.game import Game, Source
from forager.library.steamgriddb import (
    fetch_header_bytes_for_steam,
    fetch_banner_bytes_for_steam,
    fetch_grid_bytes_for_steam, fetch_grid_bytes_for_game,
    fetch_header_bytes_for_game,
    fetch_banner_bytes_for_game,
)
from forager.library.icon_provider import load_icon
from forager.utils.paths import art_cache_dir, banner_cache_dir, steam_appcache_dir

STEAM_CACHE = steam_appcache_dir()
ART_CACHE = art_cache_dir()
BANNER_CACHE = banner_cache_dir()
STEAM_CDN = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{app_id}/{name}"
STEAM_STORE_SEARCH = "https://store.steampowered.com/api/storesearch/?term={term}&l=english&cc=US"

_STEAM_APPID_CACHE: dict[str, str] = {}
_STEAM_APPID_LOCK = threading.Lock()
_STEAM_APPID_FILE = ART_CACHE / "steam_app_ids.json"
_STEAM_APPID_KEY_PREFIX = "v2:"


def _appid_cache() -> dict[str, str]:
    global _STEAM_APPID_CACHE
    if not _STEAM_APPID_CACHE:
        try:
            _STEAM_APPID_CACHE = json.loads(_STEAM_APPID_FILE.read_text("utf-8"))
        except Exception:
            _STEAM_APPID_CACHE = {}
    return _STEAM_APPID_CACHE


def _cache_appid(term: str, app_id: str | None) -> None:
    cache = _appid_cache()
    cache[_STEAM_APPID_KEY_PREFIX + term.lower()] = app_id or ""
    try:
        ART_CACHE.mkdir(parents=True, exist_ok=True)
        _STEAM_APPID_FILE.write_text(json.dumps(cache))
    except Exception:
        pass


def _steam_search_terms(game: Game) -> list[str] | None:
    """Candidate Steam store search terms, most specific first.

    ``search_names`` wins outright. Series games search their holding folder
    plus the game name before falling back to the bare name; every game keeps
    the bare (leaf) name as a last resort.
    """
    if game.search_names:
        return list(game.search_names)
    terms: list[str] = []
    plan = game.sgdb_search
    if plan:
        queries, match_term = plan
        if match_term:
            terms = [f"{q} {match_term}" for q in queries] + [match_term]
        else:
            terms = list(queries)
    name = game.name
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    leaf = name.strip()
    if leaf and (not terms or leaf != terms[-1]):
        terms.append(leaf)
    return terms or None


def _name_matches(store_name: str, term: str) -> bool:
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    n = norm(store_name)
    t = norm(term)
    if n == t:
        return True
    if len(t) >= 8 and n.startswith(t) and (len(n) == len(t) or n[len(t)] == " "):
        return True
    return False


def _steam_store_search(term: str) -> str | None:
    url = STEAM_STORE_SEARCH.format(term=urllib.parse.quote(term))
    req = urllib.request.Request(url, headers={"User-Agent": "forager/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    for it in payload.get("items") or []:
        if it.get("type") == "app" and _name_matches(it.get("name") or "", term):
            return str(it.get("id"))
    return None


def steam_app_id(game: Game) -> str | None:
    """Resolve the Steam App ID for a game.

    Steam games use their own ``app_id``. Every other game is looked up on the
    Steam store by name, accepting only confident (exact or distinctive-prefix)
    title matches so ambiguous folder names can never pull in a wrong game.
    Lookups are cached on disk per search term.
    """
    if game.app_id:
        return game.app_id
    terms = _steam_search_terms(game)
    if not terms:
        return None
    with _STEAM_APPID_LOCK:
        cache = _appid_cache()
        for term in terms:
            key = _STEAM_APPID_KEY_PREFIX + term.lower()
            if key not in cache:
                cache[key] = _steam_store_search(term) or ""
                _cache_appid(term, cache[key])
            if cache[key]:
                return cache[key]
    return None


def _ensure_cache():
    ART_CACHE.mkdir(parents=True, exist_ok=True)


def _cache_key(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:16]


def _steam_path(game: Game, filename: str) -> Path | None:
    if game.source != Source.STEAM or not game.app_id:
        return None
    p = STEAM_CACHE / game.app_id / filename
    return p if p.is_file() else None


def _cached_header_path(game: Game) -> Path | None:
    _ensure_cache()
    key = _cache_key(game.app_id or game.name)
    for ext in (".jpg", ".png"):
        p = ART_CACHE / f"header_{key}{ext}"
        if p.is_file():
            return p
    return None


def bytes_to_pixmap(data: bytes, max_size: int = 0) -> QPixmap | None:
    if not data:
        return None
    pix = QPixmap()
    if pix.loadFromData(QByteArray(data)):
        if max_size > 0 and (pix.width() > max_size or pix.height() > max_size):
            pix = pix.scaled(
                max_size, max_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pix
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA")
        if max_size > 0:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        raw = img.tobytes("raw", "RGBA")
        qimg = QImage(raw, img.width, img.height, QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimg)
    except Exception:
        return None


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


def _cached_grid_path(game: Game) -> Path | None:
    _ensure_cache()
    key = _cache_key(game.app_id or game.name)
    for ext in (".jpg", ".png"):
        p = ART_CACHE / f"grid_{key}{ext}"
        if p.is_file():
            return p
    return None


def _image_ext(data: bytes) -> str:
    return ".jpg" if data[:3] == b"\xff\xd8" else ".png"


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


def _cached_hero_path(game: Game) -> Path | None:
    BANNER_CACHE.mkdir(parents=True, exist_ok=True)
    key = _cache_key(game.app_id or game.name)
    for ext in (".jpg", ".png"):
        p = BANNER_CACHE / f"hero_{key}{ext}"
        if p.is_file():
            return p
    return None


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


def load_logo(game: Game) -> QPixmap | None:
    local = _steam_path(game, "logo.png")
    if local is not None:
        pix = QPixmap(str(local))
        if not pix.isNull():
            return pix
    return None


def placeholder_card(game: Game, width: int, height: int, name: str | None = None) -> QPixmap:
    pix = QPixmap(width, height)
    pix.fill(QColor("#141414"))

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    icon = load_icon(game, allow_network=False)
    if icon is not None:
        icon = icon.scaled(
            width // 2, height // 2,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (width - icon.width()) // 2
        y = (height - icon.height()) // 2 - 10
        p.drawPixmap(x, y, icon)

    label = (name or game.name).replace("/", " / ")
    font = QFont("Roboto", 10)
    p.setFont(font)
    fm = QFontMetrics(font)
    while fm.horizontalAdvance(label) > width - 24 and len(label) > 8:
        label = label[:-2] + "…"
    p.setPen(QColor("#8e8e8e"))
    tw = fm.horizontalAdvance(label)
    p.drawText((width - tw) // 2, height - 22, label)
    p.end()
    return pix


def scale_crop(source: QPixmap, width: int, height: int) -> QPixmap:
    if source.isNull():
        return source
    scaled = source.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (scaled.width() - width) // 2
    y = (scaled.height() - height) // 2
    return scaled.copy(x, y, width, height)


def scaled(source: QPixmap, width: int, height: int) -> QPixmap:
    if source.isNull():
        return source
    return source.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
