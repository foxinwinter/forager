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

    The source pixmap is never modified or cropped vertically: it is scaled
    proportionally to the banner height so the full art (including its bottom
    edge) always stays visible. Sources wider than the banner only have their
    horizontal overflow centre-cropped; narrower sources are fitted with a
    blurred backdrop filling the side space.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source: QPixmap | None = None
        self._overlay: QWidget | None = None
        self.setMinimumHeight(_BANNER_H)
        self.setMaximumHeight(_BANNER_H)

    def set_source(self, pix: QPixmap | None):
        self._source = pix
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
        scaled_w = src.width() * h / src.height()
        if scaled_w >= w:
            # Fills the height; only horizontal overflow is centre-cropped, so
            # the bottom of the art is always visible.
            src_w = w * src.height() / h
            sx = (src.width() - src_w) / 2
            p.drawPixmap(QRectF(0, 0, w, h), src,
                         QRectF(sx, 0, src_w, src.height()))
            return
        # Narrower than the banner: show the whole art fitted to the height,
        # with a blurred backdrop filling the side space.
        p.drawPixmap(0, 0, self._backdrop(src))
        x = (w - scaled_w) / 2
        p.drawPixmap(QRectF(x, 0, scaled_w, h), src,
                     QRectF(0, 0, src.width(), src.height()))

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
