"""Steam-style hover pop for library cards.

The hovered ``GameCard`` is rendered to a pixmap and painted scaled up (~5%)
with a soft SpaceTheme-blue glow on top of its neighbours. It is a child of
the scroll *viewport* (not the card or its host) so the scaled art can
overflow the card's own bounds and the host's rect without being clipped by
either — it only clips at the visible viewport edge, like Steam does at the
window edge. It is transparent to mouse events so the card underneath keeps
normal hover/click behaviour.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

_SCALE = 1.05
_GLOW_COLOR = QColor(75, 137, 239, 140)
_GLOW_BLUR = 30


class CardHoverPopup(QWidget):
    """Overlay that draws one card scaled up with a glow behind it."""

    def __init__(self, viewport: QWidget, parent=None):
        super().__init__(viewport)
        self._card = None
        self._base: QPixmap | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(_GLOW_BLUR)
        glow.setColor(_GLOW_COLOR)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)
        self.hide()

    def show_for(self, card):
        """Render *card* scaled up and position the popup over it (viewport coords)."""
        self._card = card
        w, h = card.width(), card.height()
        dpr = card.window().devicePixelRatioF()
        base = QPixmap(int(w * dpr), int(h * dpr))
        base.setDevicePixelRatio(dpr)
        card.render(base)
        self._base = base
        self._place()
        self.raise_()
        self.show()
        self.update()

    def _place(self):
        """Re-position over the card in viewport coordinates (card moved / scrolled)."""
        if self._card is None:
            return
        w, h = self._card.width(), self._card.height()
        nw = int(round(w * _SCALE))
        nh = int(round(h * _SCALE))
        viewport = self.parentWidget()
        p = self._card.mapTo(viewport, QPoint(0, 0))
        self.setGeometry(p.x() - (nw - w) // 2, p.y() - (nh - h) // 2, nw, nh)

    def reposition(self):
        """Update geometry after the host scrolled or re-laid out."""
        if self.isVisible():
            self._place()

    def refresh(self):
        """Re-render after the card's art changed while it is hovered."""
        if self._card is not None:
            self.show_for(self._card)

    def hide_effect(self):
        self._card = None
        self._base = None
        self.hide()

    def paintEvent(self, event):
        if self._base is None or self._base.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), self._base)
