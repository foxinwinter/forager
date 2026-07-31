from __future__ import annotations
import hashlib
import io
import json
import math
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from PySide6.QtCore import Qt, QByteArray, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QFontMetrics, QFontDatabase,
    QRadialGradient, QTextOption,
)
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
    """Sunburst-banner placeholder: the wide fallback used on the game page."""
    return _render_placeholder(game, _paint_sunburst, width, height, name)


def placeholder_grid(game: Game, width: int, height: int, name: str | None = None) -> QPixmap:
    """Glow-cover placeholder, rendered at 600x900 then cropped to the tile."""
    cover = _render_placeholder(game, _paint_glow, 600, 900, name)
    return scale_crop(cover, width, height)


# -- generated placeholder art ------------------------------------------

_PLACEHOLDER_FONT_NAME = "VT323"
_FONT_FILE = Path(__file__).resolve().parent.parent / "resources" / "fonts" / "VT323-Regular.ttf"
_PLACEHOLDER_FONT_FAMILY: str | None = None
_PLACEHOLDER_SHADOW_CACHE: dict[int, QImage] = {}


def register_placeholder_font() -> str:
    """Register the bundled VT323 font and return its family name.

    Called at app startup and lazily again before any placeholder renders, so
    it also works for tests and workers. Falls back to the font name when the
    font cannot be registered (e.g. no QApplication yet).
    """
    global _PLACEHOLDER_FONT_FAMILY
    if _PLACEHOLDER_FONT_FAMILY is None:
        family = None
        if _FONT_FILE.is_file():
            try:
                fid = QFontDatabase.addApplicationFont(str(_FONT_FILE))
                if fid != -1:
                    fams = QFontDatabase.applicationFontFamilies(fid)
                    if fams:
                        family = fams[0]
            except Exception:
                family = None
        _PLACEHOLDER_FONT_FAMILY = family or _PLACEHOLDER_FONT_NAME
    return _PLACEHOLDER_FONT_FAMILY


def _black_shadow(pix: QPixmap, blur_scale: int = 8, dx: int = 3, dy: int = 3,
                  alpha: int = 158) -> QImage:
    """Soft black silhouette of *pix* offset down-right (light from top-left).

    The buffer is sized so the blur never clips at the edge, keeping the
    shadow small without a hard cutoff on the bottom/right.
    """
    key = pix.cacheKey()
    cached = _PLACEHOLDER_SHADOW_CACHE.get(key)
    if cached is not None:
        return cached
    img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    mask = QImage(w, h, QImage.Format.Format_ARGB32)
    mask.fill(QColor(0, 0, 0, 255))
    mp = QPainter(mask)
    mp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    mp.drawImage(0, 0, img)
    mp.end()
    small = mask.scaled(
        max(2, w // blur_scale), max(2, h // blur_scale),
        Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
    )
    blurred = small.scaled(
        w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation,
    )
    m = 12
    out = QImage(w + 2 * m, h + 2 * m, QImage.Format.Format_ARGB32)
    out.fill(Qt.GlobalColor.transparent)
    op = QPainter(out)
    op.setOpacity(alpha / 255.0)
    op.drawImage(m + dx, m + dy, blurred)
    op.end()
    _PLACEHOLDER_SHADOW_CACHE[key] = out
    return out


def _draw_placeholder_icon(p: QPainter, icon: QPixmap | None, w: int, h: int,
                           h_frac: float = 0.30) -> int | None:
    """Centered icon (no card), with the soft bottom-right shadow; returns the
    bottom of the drawn icon for text placement."""
    if icon is None:
        return None
    side = int(h * 0.38)
    scaled = icon.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    x = (w - scaled.width()) // 2
    y = int(h * h_frac - scaled.height() / 2)
    p.drawImage(x - 12, y - 12, _black_shadow(scaled))
    p.drawPixmap(x, y, scaled)
    return y + scaled.height()


def _draw_placeholder_text(p: QPainter, text: str, rect: list[int], pts: int = 30):
    """Lowercase, letter-spaced VT323 title, centered and word-wrapped."""
    font = QFont(register_placeholder_font())
    font.setPointSize(pts)
    font.setWeight(QFont.Weight.Normal)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
    p.setFont(font)
    p.setPen(QColor("#cdd6e2"))
    opt = QTextOption(Qt.AlignmentFlag.AlignCenter)
    opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    p.drawText(QRectF(float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])), text, opt)


def _paint_glow(p: QPainter, w: int, h: int):
    g = QRadialGradient(QPointF(w * 0.5, h * 0.32), max(w, h) * 0.7)
    g.setColorAt(0.0, QColor("#222a36"))
    g.setColorAt(1.0, QColor("#0f141b"))
    p.fillRect(0, 0, w, h, g)


def _paint_sunburst(p: QPainter, w: int, h: int):
    g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.75)
    g.setColorAt(0.0, QColor("#262e3a"))
    g.setColorAt(1.0, QColor("#0f141b"))
    p.fillRect(0, 0, w, h, g)
    p.setPen(QColor(255, 255, 255, 13))
    cx, cy = w / 2, h / 2
    for deg in range(0, 360, 7):
        rad = math.radians(deg)
        p.drawLine(int(cx), int(cy),
                   int(cx + math.cos(rad) * max(w, h)),
                   int(cy + math.sin(rad) * max(w, h)))


def _local_icon_pixmap(game: Game) -> QPixmap | None:
    """Raw local icon (folder icon / .minecraft/icon.png) at full resolution,
    unlike the 48px-capped ``load_icon``."""
    for name in ("icon.png", "icon.ico", "icon.svg", "Icon.png", "Icon.ico"):
        candidate = game.path / name
        if candidate.is_file():
            pix = QPixmap(str(candidate))
            if not pix.isNull():
                return pix
    mc = game.path / ".minecraft/icon.png"
    if mc.is_file():
        pix = QPixmap(str(mc))
        if not pix.isNull():
            return pix
    return None


def _placeholder_icon(game: Game) -> QPixmap | None:
    raw = _local_icon_pixmap(game)
    if raw is not None:
        return raw
    return load_icon(game, allow_network=False)


def _render_placeholder(game: Game, background, width: int, height: int,
                        name: str | None = None) -> QPixmap:
    pix = QPixmap(width, height)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    background(p, width, height)
    bottom = _draw_placeholder_icon(p, _placeholder_icon(game), width, height, 0.30)
    if bottom is None:
        text_rect = [int(width * 0.08), int(height * 0.60), int(width * 0.84), int(height * 0.30)]
    else:
        text_rect = [int(width * 0.08), bottom + int(height * 0.04),
                     int(width * 0.84), int(height - bottom - height * 0.08)]
    _draw_placeholder_text(p, (name or game.name).replace("/", " / "), text_rect)
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
