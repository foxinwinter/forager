"""Steam-style hover pop for library cards.

Mirrors the Steam client's card hover (as themed by SpaceTheme / the
SteamUI skins that restyle the real client): a smooth ~0.2s ease transition
that lifts the hovered card over its neighbours with a soft dark drop shadow
(``box-shadow: 0px 14px 12px 0px rgb(0 0 0 / 30%)``). On the cover itself the
tile **brightens** (``filter: brightness(1.1)``) — the "slight shine" — and a
faint diagonal glare sweeps in from the tile's **upper-right corner** once, the
classic Steam shimmer. No outline/glow ring.

The popup is a child of the scroll *viewport* (not the card or its host) so the
scaled art can overflow the card's own bounds and the host's rect without
being clipped by either, and it is clamped to stay fully inside the viewport so
nothing clips at the window edge. It is transparent to mouse events so the card
underneath keeps normal hover/click behaviour.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QPoint, QRectF, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QLinearGradient
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from forager.ui.theme import C

_SCALE = 1.04
_TRANSITION_MS = 200
_SHADOW_COLOR = QColor(0, 0, 0, 110)
_SHADOW_BLUR = 16
_SHADOW_OFFSET = (0, 3)
_EDGE_INSET = 6
_BRIGHTNESS_ALPHA = 42
_GLARE_PEAK = 30
_GLARE_START = -0.15
_GLARE_END = 1.15
_GLARE_WIDTH = 0.12
_RADIUS = C.RADIUS


class CardHoverPopup(QWidget):
    """Overlay that animates one card lifted, brightened, with a glare sweep."""

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
        """Render *card* lifted, animate it in over the card (viewport coords)."""
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
        """Position over the card in viewport coords, clamped so nothing clips.

        The popup is centred over its card; when the card sits near a viewport
        edge the centred geometry would hang outside and get clipped, so it is
        clamped (with a small inset) to stay fully visible.
        """
        if self._card is None:
            return
        w, h = self._card.width(), self._card.height()
        nw = int(round(w * _SCALE))
        nh = int(round(h * _SCALE))
        viewport = self.parentWidget()
        p = self._card.mapTo(viewport, QPoint(0, 0))
        x = p.x() - (nw - w) // 2
        y = p.y() - (nh - h) // 2
        x = max(_EDGE_INSET, min(x, viewport.width() - nw - _EDGE_INSET))
        y = max(_EDGE_INSET, min(y, viewport.height() - nh - _EDGE_INSET))
        self.setGeometry(x, y, nw, nh)

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
        """Steam's cover shine: brighten + a glare sweep from the upper-right.

        The whole cover lifts in brightness (Steam's ``brightness(1.1)``),
        and a faint diagonal band of light sweeps once from the tile's
        upper-right corner towards the lower-left, clipped to the cover's
        rounded corners. Both fade in with the popup's ease.
        """
        a = self._progress
        if a <= 0.0:
            return
        radius = _RADIUS * _SCALE
        clip = QPainterPath()
        clip.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.save()
        p.setClipPath(clip)
        p.fillRect(rect, QColor(255, 255, 255, int(round(_BRIGHTNESS_ALPHA * a))))

        pos = _GLARE_START + (_GLARE_END - _GLARE_START) * a
        peak = int(round(_GLARE_PEAK * a))
        lo = min(1.0, max(0.0, pos - _GLARE_WIDTH))
        mid = min(1.0, max(0.0, pos))
        hi = min(1.0, max(0.0, pos + _GLARE_WIDTH))
        grad = QLinearGradient(rect.topRight(), rect.bottomLeft())
        grad.setColorAt(lo, QColor(255, 255, 255, 0))
        grad.setColorAt(mid, QColor(255, 255, 255, peak))
        grad.setColorAt(hi, QColor(255, 255, 255, 0))
        p.fillRect(rect, grad)
        p.restore()
