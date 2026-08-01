"""Steam-style hero banner for the game page."""
from __future__ import annotations
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPixmap, QColor, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from forager.ui.theme import C

_BANNER_H = 420
_BLUR_RADIUS = 26
_FEATHER = 130


def _to_pil(pix: QPixmap):
    from PIL import Image
    img = pix.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes("RGBA", (img.width(), img.height()),
                           bytes(img.constBits()), "raw", "RGBA", 0, 1)


def _from_pil(pil) -> QPixmap:
    raw = pil.tobytes("raw", "RGBA")
    qimg = QImage(raw, pil.width, pil.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


def _gaussian_blur(pix: QPixmap, radius: float) -> QPixmap:
    from PIL import ImageFilter
    return _from_pil(_to_pil(pix).filter(ImageFilter.GaussianBlur(radius)))


def _feather_edges(pix: QPixmap, fade: int, horizontal=True,
                   vertical=True) -> QPixmap:
    """Fade the pixmap's edges to transparent over ``fade`` pixels."""
    from PIL import Image, ImageChops
    if fade <= 0:
        return pix
    w, h = pix.width(), pix.height()
    combined = None
    if horizontal:
        row = bytearray(w)
        for x in range(w):
            d = min(x, w - 1 - x)
            row[x] = min(255, int(255 * d / fade))
        combined = Image.frombytes("L", (w, 1), bytes(row)).resize((w, h))
    if vertical:
        col = bytearray(h)
        for y in range(h):
            d = min(y, h - 1 - y)
            col[y] = min(255, int(255 * d / fade))
        vmask = Image.frombytes("L", (h, 1), bytes(col)).resize((w, h))
        combined = vmask if combined is None else ImageChops.multiply(combined, vmask)
    if combined is None:
        return pix
    pil = _to_pil(pix).convert("RGB").convert("RGBA")
    pil.putalpha(combined)
    return _from_pil(pil)


class Banner(QWidget):
    """Wide hero image with the Play-overlay area on top.

    Real art is shown whole and centred with feathered edges over a blurred
    cover-fill of the same art, so it reads edge-to-edge with no hard backdrop
    band, no crop and no stretch. When ``fit`` is set (generated placeholder
    art) the art is shown whole, centred, over a blurred backdrop filling the
    leftover space.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source: QPixmap | None = None
        self._fit = False
        self._overlay: QWidget | None = None
        self._backdrop_cache: tuple | None = None
        self._crisp_cache: tuple | None = None
        self.setMinimumHeight(_BANNER_H)
        self.setMaximumHeight(_BANNER_H)

    def set_source(self, pix: QPixmap | None, fit: bool = False):
        self._source = pix
        self._fit = fit
        self._backdrop_cache = None
        self._crisp_cache = None
        self.update()

    def set_overlay(self, overlay: QWidget):
        self._overlay = overlay
        if overlay is not None:
            overlay.setParent(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay is not None:
            self._overlay.setGeometry(self.rect())

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setBrush(QColor(C.COLOR_1))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), C.RADIUS, C.RADIUS)
        if self._source is None or self._source.isNull():
            return

        p.save()
        p.setClipPath(self._clip_path())
        self._paint_art(p)
        p.restore()

    def _paint_art(self, p: QPainter):
        w, h = self.width(), self.height()
        src = self._source
        sw, sh = src.width(), src.height()
        scale = min(w / sw, h / sh)
        disp_w, disp_h = sw * scale, sh * scale
        p.drawPixmap(0, 0, self._backdrop(src))
        if self._fit:
            # Generated placeholder art: show it whole, centred, over the
            # blurred backdrop.
            p.drawPixmap(QRectF((w - disp_w) / 2, (h - disp_h) / 2,
                                disp_w, disp_h),
                         src, QRectF(0, 0, sw, sh))
            return
        # Seamless: the full art centred with feathered edges melting into the
        # blurred backdrop — no crop, no stretch, no visible seam.
        p.drawPixmap(QRectF((w - disp_w) / 2, (h - disp_h) / 2,
                            disp_w, disp_h),
                     self._crisp(src), QRectF(0, 0, disp_w, disp_h))

    def _backdrop(self, pix: QPixmap) -> QPixmap:
        """Gaussian-blurred cover-fill of *pix* matching the widget size."""
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0 or pix.isNull():
            return pix
        key = (pix.cacheKey(), w, h)
        if self._backdrop_cache is not None and self._backdrop_cache[0] == key:
            return self._backdrop_cache[1]
        k = max(w / pix.width(), h / pix.height())
        cover = pix.scaled(
            int(pix.width() * k), int(pix.height() * k),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (cover.width() - w) // 2
        y = (cover.height() - h) // 2
        cover = cover.copy(x, y, w, h)
        blurred = _gaussian_blur(cover, _BLUR_RADIUS)
        self._backdrop_cache = (key, blurred)
        return blurred

    def _crisp(self, pix: QPixmap) -> QPixmap:
        """Fit-scaled *pix* with its edges feathered towards the backdrop."""
        w, h = self.width(), self.height()
        key = (pix.cacheKey(), w, h)
        if self._crisp_cache is not None and self._crisp_cache[0] == key:
            return self._crisp_cache[1]
        scaled = pix.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        feathered = _feather_edges(
            scaled, _FEATHER,
            horizontal=scaled.width() < w,
            vertical=scaled.height() < h,
        )
        self._crisp_cache = (key, feathered)
        return feathered

    def _clip_path(self):
        path = QPainterPath()
        path.addRoundedRect(self.rect(), C.RADIUS, C.RADIUS)
        return path
