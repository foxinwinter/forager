"""Steam-style hero banner for the game page."""
from __future__ import annotations
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from forager.ui.theme import C

_BANNER_H = 420
_BLUR_DIVISOR = 12


class Banner(QWidget):
    """Wide hero image with the Play-overlay area on top.

    Mirrors how the Steam client renders its hero: the art is scaled to cover
    the banner box edge-to-edge and its overflow is centre-cropped, so there is
    never a backdrop band. When ``fit`` is set (generated placeholder art) the
    art is instead shown whole, centred, with a blurred backdrop filling the
    leftover space.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source: QPixmap | None = None
        self._fit = False
        self._overlay: QWidget | None = None
        self.setMinimumHeight(_BANNER_H)
        self.setMaximumHeight(_BANNER_H)

    def set_source(self, pix: QPixmap | None, fit: bool = False):
        self._source = pix
        self._fit = fit
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
        if self._fit:
            # Generated placeholder art: show it whole, centred, with a blurred
            # backdrop filling the leftover space.
            scale = min(w / sw, h / sh)
            disp_w, disp_h = sw * scale, sh * scale
            p.drawPixmap(0, 0, self._backdrop(src))
            p.drawPixmap(QRectF((w - disp_w) / 2, (h - disp_h) / 2,
                                disp_w, disp_h),
                         src, QRectF(0, 0, sw, sh))
            return
        # Cover like the Steam client's object-fit: cover: the art always fills
        # the box edge-to-edge and its overflow is centre-cropped, so there is
        # never a backdrop band.
        if sw * h >= sh * w:
            src_w = w * sh / h
            sx = (sw - src_w) / 2
            p.drawPixmap(QRectF(0, 0, w, h), src,
                         QRectF(sx, 0, src_w, sh))
        else:
            src_h = h * sw / w
            sy = (sh - src_h) / 2
            p.drawPixmap(QRectF(0, 0, w, h), src,
                         QRectF(0, sy, sw, src_h))

    def _backdrop(self, pix: QPixmap) -> QPixmap:
        small = pix.scaled(
            max(1, pix.width() // _BLUR_DIVISOR),
            max(1, pix.height() // _BLUR_DIVISOR),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        return small.scaled(
            self.width(), self.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _clip_path(self):
        path = QPainterPath()
        path.addRoundedRect(self.rect(), C.RADIUS, C.RADIUS)
        return path
