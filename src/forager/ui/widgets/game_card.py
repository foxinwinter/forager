from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QFont, QFontMetrics, QPixmap, QLinearGradient
from PySide6.QtWidgets import QWidget

from forager.core.game import Game
from forager.services import art
from forager.ui.theme import C

CARD_W = 232
CARD_H = 348
_RADIUS = C.RADIUS


class GameCard(QWidget):
    clicked = Signal(object)
    activated = Signal(object)
    hover_changed = Signal(object, bool)

    def __init__(
        self,
        game: Game,
        parent=None,
        card_w: int = CARD_W,
        card_h: int = CARD_H,
        fit_art: bool = False,
    ):
        super().__init__(parent)
        self.game = game
        self._focused = False
        self._art: QPixmap | None = None
        self._fit_art = fit_art

        self.setFixedSize(card_w, card_h)
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

        w, h = self.width(), self.height()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, _RADIUS, _RADIUS)
        p.setClipPath(path)

        p.fillRect(rect, QColor(C.COLOR_3))
        if self._art is not None and not self._art.isNull():
            if self._fit_art:
                pix = art.scaled(self._art, w, h)
                p.drawPixmap(
                    (w - pix.width()) // 2,
                    (h - pix.height()) // 2,
                    pix,
                )
            else:
                p.drawPixmap(self.rect(), art.scale_crop(self._art, w, h))
        else:
            self._paint_placeholder(p, w, h)

        if self._overlay_visible():
            self._paint_overlay(p, w, h)

        p.setClipping(False)

    def _fallback_art(self) -> QPixmap | None:
        size = (self.width(), self.height())
        if getattr(self, "_fallback", None) is None or self._fallback_size != size:
            self._fallback = art.placeholder_grid(self.game, size[0], size[1])
            self._fallback_size = size
        return self._fallback

    def _paint_placeholder(self, p: QPainter, w: int, h: int):
        pix = self._fallback_art()
        if pix is not None and not pix.isNull():
            p.drawPixmap(self.rect(), pix)
            return
        self._paint_simple_placeholder(p, w, h)

    def _paint_simple_placeholder(self, p: QPainter, w: int, h: int):
        icon = art.load_icon(self.game, allow_network=False)
        if icon is not None:
            side = max(36, w // 3)
            icon = icon.scaled(
                side, side,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(
                (w - icon.width()) // 2,
                max(6, h // 2 - icon.height() // 2 - 24),
                icon,
            )

        label = self.game.name.replace("/", " / ")
        font = QFont("Roboto", max(9, w // 21), QFont.Weight.Medium)
        p.setFont(font)
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(label) > w - 24 and len(label) > 10:
            label = label[:-3] + "…"
        p.setPen(QColor(C.TEXT_DIM))
        p.drawText(
            QRectF(12, h - 40, w - 24, 24),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )

    def _paint_overlay(self, p: QPainter, w: int, h: int):
        overlay_h = max(44, h // 5)
        grad = QLinearGradient(0, h - overlay_h, 0, h)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(1, QColor(0, 0, 0, 205))
        p.fillRect(QRectF(0, h - overlay_h, w, overlay_h), grad)

        label = self.game.name.replace("/", " / ")
        font = QFont("Roboto", max(10, w // 19), QFont.Weight.DemiBold)
        p.setFont(font)
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(label) > w - 20 and len(label) > 10:
            label = label[:-3] + "…"
        p.setPen(QColor(C.TEXT))
        p.drawText(
            QRectF(10, h - overlay_h + 8, w - 20, overlay_h - 12),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )

    def set_focused(self, focused: bool):
        self._focused = focused
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.hover_changed.emit(self, True)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hover_changed.emit(self, False)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.game)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.game)
