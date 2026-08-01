"""Steam-style hero banner for the game page."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from forager.services import art
from forager.ui.theme import C

_BANNER_H = 420
_BLUR_DIVISOR = 12


class Banner(QWidget):
    """Wide hero image with the Play-overlay area on top.

    Small sources are upscaled to fill the banner; large sources are scaled
    down to fit sharp and whole, with a blurred stretched copy of the artwork
    filling any leftover space (Steam's side-blur backdrop).
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

    def _backdrop(self, pix: QPixmap) -> QPixmap:
        """Steam-style blurred fill: stretch the artwork to cover the banner
        and soften it by downscaling then smoothing back up."""
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

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        radius = C.RADIUS
        p.setBrush(QColor(C.COLOR_3))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), radius, radius)
        if self._source is None or self._source.isNull():
            return

        p.save()
        p.setClipPath(self._clip_path())
        self._paint_steam_style(p)
        p.restore()

    def _clip_path(self):
        path = QPainterPath()
        path.addRoundedRect(self.rect(), C.RADIUS, C.RADIUS)
        return path

    def _paint_steam_style(self, p: QPainter):
        w, h = self.width(), self.height()
        src = self._source

        if src.width() < w or src.height() < h:
            p.drawPixmap(0, 0, art.scale_crop(src, w, h))
            return

        fitted = src.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        if fitted.width() < w or fitted.height() < h:
            p.drawPixmap(0, 0, self._backdrop(src))

        x = (w - fitted.width()) // 2
        y = (h - fitted.height()) // 2
        p.drawPixmap(x, y, fitted)
