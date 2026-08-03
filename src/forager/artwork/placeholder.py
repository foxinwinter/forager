"""Generated placeholder art for games with no cover art at all.

``placeholder_card`` renders the sunburst banner used on the game page;
``placeholder_grid`` renders the glow cover used for grid tiles. Both draw the
game's local icon (bare, no card) with a soft black shadow offset to the
bottom-right, then the game name in bundled VT323 type.
"""
from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QFontDatabase,
    QRadialGradient, QTextOption,
)

from forager.core.game import Game
from forager.core.paths import resources_dir
from forager.services.icon_provider import load_icon
from forager.artwork.pixmap_utils import scale_crop

_PLACEHOLDER_FONT_NAME = "VT323"
_FONT_FILE = resources_dir() / "fonts" / "VT323-Regular.ttf"
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


def placeholder_card(game: Game, width: int, height: int, name: str | None = None) -> QPixmap:
    """Sunburst-banner placeholder: the wide fallback used on the game page."""
    return _render_placeholder(game, _paint_sunburst, width, height, name)


def placeholder_grid(game: Game, width: int, height: int, name: str | None = None) -> QPixmap:
    """Glow-cover placeholder, rendered at 600x900 then cropped to the tile."""
    cover = _render_placeholder(game, _paint_glow, 600, 900, name, pts=125)
    return scale_crop(cover, width, height)


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
    """Raw local icon (folder icon / .minecraft/icon.png / embedded .exe icon)
    at full resolution, unlike the 48px-capped ``load_icon``."""
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
    return _exe_icon_pixmap(game.path)


def _exe_icon_pixmap(path: Path) -> QPixmap | None:
    from forager.artwork.pe_icons import best_icon, find_exe_with_icon

    exe = find_exe_with_icon(path)
    if exe is None:
        return None
    try:
        im = best_icon(exe)
    except Exception:
        return None
    if im is None:
        return None
    qimg = QImage(im.tobytes("raw", "RGBA"), im.width, im.height,
                  QImage.Format.Format_RGBA8888)
    if qimg.isNull():
        return None
    return QPixmap.fromImage(qimg)


def _placeholder_icon(game: Game) -> QPixmap | None:
    raw = _local_icon_pixmap(game)
    if raw is not None:
        return raw
    return load_icon(game, allow_network=False)


def _render_placeholder(game: Game, background, width: int, height: int,
                        name: str | None = None, pts: int = 46) -> QPixmap:
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
    _draw_placeholder_text(p, (name or game.name).replace("/", " / "), text_rect, pts)
    p.end()
    return pix
