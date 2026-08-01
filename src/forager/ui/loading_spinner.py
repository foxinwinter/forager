from __future__ import annotations
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from forager.ui.theme import C


def _hex(color: str) -> tuple:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(24, 24)
        p.rotate(self._angle)
        for i in range(8):
            alpha = 255 - (i * 32)
            p.setBrush(QColor(*_hex(C.ACCENT_1), alpha))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(-3, -16, 6, 6)
            p.rotate(45)
