from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPen, QPainter, QPainterPath, QFont, QFontMetrics, QPixmap, QLinearGradient
from PySide6.QtWidgets import QWidget

from gamehub.core.game import Game
from gamehub.services import art
from gamehub.ui.theme import C

CARD_W = 232
CARD_H = 348
_RADIUS = C.RADIUS
_OVERLAY_H = 68


class GameCard(QWidget):
    clicked = Signal(object)
    activated = Signal(object)

    def __init__(self, game: Game, parent=None):
        super().__init__(parent)
        self.game = game
        self._focused = False
        self._art: QPixmap | None = None

        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_art(self, pix: QPixmap | None):
        self._art = pix
        self.update()

    def _overlay_visible(self) -> bool:
        return self._focused or self.underMouse()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, _RADIUS, _RADIUS)
        p.setClipPath(path)

        p.fillRect(rect, QColor(C.COLOR_3))
        if self._art is not None and not self._art.isNull():
            p.drawPixmap(self.rect(), art.scale_crop(self._art, CARD_W, CARD_H))
        else:
            self._paint_placeholder(p)

        if self._overlay_visible():
            self._paint_overlay(p)

        p.setClipping(False)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self._focused:
            p.setPen(QPen(QColor(C.ACCENT_1), 2))
            p.drawRoundedRect(rect, _RADIUS, _RADIUS)
        elif self.underMouse():
            p.setPen(QPen(QColor(255, 255, 255, 45), 1))
            p.drawRoundedRect(rect, _RADIUS, _RADIUS)

    def _paint_placeholder(self, p: QPainter):
        icon = art.load_icon(self.game, allow_network=False)
        if icon is not None:
            icon = icon.scaled(
                72, 72,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap((CARD_W - icon.width()) // 2, CARD_H // 2 - 64, icon)

        label = self.game.name.replace("/", " / ")
        font = QFont("Roboto", 11, QFont.Weight.Medium)
        p.setFont(font)
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(label) > CARD_W - 24 and len(label) > 10:
            label = label[:-3] + "…"
        p.setPen(QColor(C.TEXT_DIM))
        p.drawText(
            QRectF(12, CARD_H - 44, CARD_W - 24, 24),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )

    def _paint_overlay(self, p: QPainter):
        grad = QLinearGradient(0, CARD_H - _OVERLAY_H, 0, CARD_H)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(1, QColor(0, 0, 0, 205))
        p.fillRect(QRectF(0, CARD_H - _OVERLAY_H, CARD_W, _OVERLAY_H), grad)

        label = self.game.name.replace("/", " / ")
        font = QFont("Roboto", 12, QFont.Weight.DemiBold)
        p.setFont(font)
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(label) > CARD_W - 20 and len(label) > 10:
            label = label[:-3] + "…"
        p.setPen(QColor(C.TEXT))
        p.drawText(
            QRectF(10, CARD_H - _OVERLAY_H + 12, CARD_W - 20, _OVERLAY_H - 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )

    def set_focused(self, focused: bool):
        self._focused = focused
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.game)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.game)
