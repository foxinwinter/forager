"""Steam-style hero banner for the game page."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from forager.ui.theme import C

_BANNER_H = 420


class Banner(QWidget):
    """Wide hero image with the Play-overlay area on top.

    The source pixmap is never modified: it is drawn stretched to cover the
    whole banner widget at paint time.
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
        radius = C.RADIUS
        p.setBrush(QColor(C.COLOR_3))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), radius, radius)
        if self._source is None or self._source.isNull():
            return

        p.save()
        p.setClipPath(self._clip_path())
        p.drawPixmap(self.rect(), self._source)
        p.restore()

    def _clip_path(self):
        path = QPainterPath()
        path.addRoundedRect(self.rect(), C.RADIUS, C.RADIUS)
        return path
