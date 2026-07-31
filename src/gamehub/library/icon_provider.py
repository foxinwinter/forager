from __future__ import annotations
import hashlib
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from gamehub.core.game import Game, Source
from gamehub.library.steamgriddb import (
    fetch_icon_bytes_for_steam, fetch_icon_bytes_for_game,
)
from gamehub.utils.paths import icon_cache_dir, steam_appcache_dir

STEAM_CACHE = steam_appcache_dir()
ICON_CACHE = icon_cache_dir()


def _ensure_cache():
    ICON_CACHE.mkdir(parents=True, exist_ok=True)


def _cache_key(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:16]


def _cached_icon_path(game: Game) -> Path | None:
    _ensure_cache()
    key = _cache_key(game.app_id or game.name)
    path = ICON_CACHE / f"{key}.png"
    return path if path.is_file() else None


def _save_icon_bytes(game: Game, data: bytes):
    _ensure_cache()
    key = _cache_key(game.app_id or game.name)
    (ICON_CACHE / f"{key}.png").write_bytes(data)


def load_icon_bytes(game: Game, allow_network: bool = True) -> bytes | None:
    cached = _cached_icon_path(game)
    if cached is not None:
        return cached.read_bytes()

    if not allow_network:
        return None

    data = None
    if game.source == Source.STEAM and game.app_id:
        data = fetch_icon_bytes_for_steam(game.app_id)
    if data is None:
        data = fetch_icon_bytes_for_game(game)
    if data:
        _save_icon_bytes(game, data)
    return data


def load_icon(game: Game, allow_network: bool = True) -> QPixmap | None:
    cached = _cached_icon_path(game)
    if cached is not None:
        return QPixmap(str(cached))

    pix = None
    if game.app_id:
        pix = _load_steam_logo(game.app_id)
    if pix is None:
        pix = _load_game_icon_direct(game)
    if pix is None and allow_network:
        from gamehub.services.art import bytes_to_pixmap

        data = load_icon_bytes(game, True)
        if data:
            return bytes_to_pixmap(data)
    if pix:
        data = _pixmap_to_bytes(pix)
        if data:
            _save_icon_bytes(game, data)
    return pix


def _pixmap_to_bytes(pix: QPixmap) -> bytes | None:
    from PySide6.QtCore import QBuffer

    buf = QBuffer()
    if not buf.open(QBuffer.OpenModeFlag.WriteOnly):
        return None
    if pix.save(buf, "PNG"):
        return bytes(buf.data())
    return None


def _load_steam_logo(app_id: str | None) -> QPixmap | None:
    if not app_id:
        return None
    logo = STEAM_CACHE / app_id / "logo.png"
    if not logo.is_file():
        return None
    img = QImage(str(logo))
    if img.isNull():
        return None
    size = min(img.width(), img.height())
    if size == 0:
        return None
    offset_x = (img.width() - size) // 2
    offset_y = (img.height() - size) // 2
    square = img.copy(offset_x, offset_y, size, size)
    return QPixmap.fromImage(square).scaled(
        48, 48, Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )


def _load_game_icon_direct(game: Game) -> QPixmap | None:
    for name in ("icon.png", "icon.ico", "icon.svg", "Icon.png", "Icon.ico"):
        candidate = game.path / name
        if candidate.is_file():
            pix = QPixmap(str(candidate))
            if not pix.isNull():
                return pix.scaled(
                    48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
    mc_icon = game.path / ".minecraft/icon.png"
    if mc_icon.is_file():
        pix = QPixmap(str(mc_icon))
        if not pix.isNull():
            return pix.scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
    return None
