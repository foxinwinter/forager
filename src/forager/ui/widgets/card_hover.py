"""Steam-style hover pop for library cards.

Mirrors the Steam client's card hover (as themed by SpaceTheme): a smooth
~0.2s ease transition that scales the hovered card up (~4%) and lifts it with
a soft dark drop shadow (``0px 4px 8px rgb(0 0 0 / 25%)``) over its
neighbours — no outline/glow ring. A faint diagonal band of light (the Steam
capsule "shine": ``linear-gradient(315deg, …)``) fades in over the cover,
fading with the same ease as the lift.

The popup is a child of the scroll *viewport* (not the card or its host) so
the scaled art can overflow the card's own bounds and the host's rect without
being clipped by either — it only clips at the visible viewport edge, like
Steam does at the window edge. It is transparent to mouse events so the card
underneath keeps normal hover/click behaviour.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QPoint, QRectF, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QLinearGradient
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from forager.ui.theme import C

_SCALE = 1.04
_RADIUS = C.RADIUS
_TRANSITION_MS = 200
_SHADOW_COLOR = QColor(0, 0, 0, 110)
_SHADOW_BLUR = 16
_SHADOW_OFFSET = (0, 3)
_SHINE_PEAK = 62


class CardHoverPopup(QWidget):
    """Overlay that animates one card scaled up with a soft shadow behind it."""

    def __init__(self, viewport: QWidget, parent=None):
        super().__init__(viewport)
        self._card = None
        self._base: QPixmap | None = None
        self._progress = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(_SHADOW_BLUR)
        shadow.setColor(_SHADOW_COLOR)
        shadow.setOffset(*_SHADOW_OFFSET)
        self.setGraphicsEffect(shadow)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(_TRANSITION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_progress)
        self.hide()

    def _set_progress(self, value):
        self._progress = float(value)
        self.update()

    def show_for(self, card):
        """Render *card* scaled up, animate it in over the card (viewport coords)."""
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
        self._anim.stop()
        self._anim.setStartValue(self._progress if self._progress > 0 else 0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

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
        self._anim.stop()
        self._card = None
        self._base = None
        self._progress = 0.0
        self.hide()

    def paintEvent(self, event):
        if self._base is None or self._base.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scale = 1.0 + (_SCALE - 1.0) * self._progress
        nw = max(1, int(round(self._base.width() * scale)))
        nh = max(1, int(round(self._base.height() * scale)))
        x = (self.width() - nw) // 2
        y = (self.height() - nh) // 2
        p.drawPixmap(x, y, nw, nh, self._base)
        self._paint_shine(p, QRectF(x, y, nw, nh))

    def _paint_shine(self, p: QPainter, rect: QRectF):
        """Steam's capsule shine: a faint diagonal band of light over the cover.

        A ``linear-gradient(315deg, …)`` highlight centered on the cover's
        diagonal with soft edges. It fades in with the popup's ease so it
        brightens as the card lifts, exactly like the Steam tile.
        """
        a = self._progress
        if a <= 0.0:
            return
        radius = _RADIUS * _SCALE
        clip = QPainterPath()
        clip.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.save()
        p.setClipPath(clip)
        peak = int(round(_SHINE_PEAK * a))
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.00, QColor(255, 255, 255, 0))
        grad.setColorAt(0.40, QColor(255, 255, 255, 0))
        grad.setColorAt(0.50, QColor(255, 255, 255, peak))
        grad.setColorAt(0.60, QColor(255, 255, 255, 0))
        grad.setColorAt(1.00, QColor(255, 255, 255, 0))
        p.fillRect(rect, grad)
        p.restore()
