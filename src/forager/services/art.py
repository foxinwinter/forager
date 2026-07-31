from __future__ import annotations
import hashlib
import io
import urllib.request
from pathlib import Path
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QFontMetrics
from forager.core.game import Game, Source
from forager.library.steamgriddb import (
    fetch_header_bytes_for_steam,
    fetch_grid_bytes_for_steam, fetch_grid_bytes_for_game,
    fetch_header_bytes_for_game,
)
from forager.library.icon_provider import load_icon
from forager.utils.paths import art_cache_dir, steam_appcache_dir

STEAM_CACHE = steam_appcache_dir()
ART_CACHE = art_cache_dir()
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
    if game.source == Source.STEAM and game.app_id:
        data = fetch_header_bytes_for_steam(game.app_id)
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


def _steam_cdn_grid_bytes(app_id: str) -> bytes | None:
    for name in ("library_600x900.jpg", "library_600x900_2x.jpg"):
        url = STEAM_CDN.format(app_id=app_id, name=name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "forager/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except Exception:
            continue
    return None


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
    if game.source == Source.STEAM and game.app_id:
        data = _steam_cdn_grid_bytes(game.app_id)
    if data is None:
        data = fetch_grid_bytes_for_steam(game.app_id) if game.source == Source.STEAM and game.app_id else None
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


def load_hero_bytes(game: Game, allow_network: bool = True) -> bytes | None:
    for name in ("library_hero.jpg", "library_hero_blur.jpg"):
        local = _steam_path(game, name)
        if local is not None:
            return local.read_bytes()
    return load_header_bytes(game, allow_network)


def load_hero(game: Game, allow_network: bool = True) -> QPixmap | None:
    for name in ("library_hero.jpg", "library_hero_blur.jpg", "header.jpg"):
        local = _steam_path(game, name)
        if local is not None:
            pix = QPixmap(str(local))
            if not pix.isNull():
                return pix
    header = load_header(game, allow_network)
    if header is not None:
        return header
    return None


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
