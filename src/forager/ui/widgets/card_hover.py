"""Steam-style hover lift for library cards.

Faithful to the Steam client's grid-tile hover (as documented by the
SteamUI skins that restyle the real client — e.g. SteamUI-OldGlory's
"Remove Zoom" tweak targets the base rule):

    .appportrait_LibraryItemBox:hover {
        transform: rotateX(3deg) translateZ(15px);
        filter: brightness(1.1) contrast(0.95) saturate(1);
        box-shadow: 0px 14px 12px 0px rgba(0, 0, 0, 0.3);
        z-index: 12;
    }

So the hovered card does not just scale: it **tilts back 3°** around its X
axis (a real perspective projection, not a flat scale), **lifts forward**
(translateZ 15px → ~1.5% bigger), **brightens** with Steam's exact
brightness/contrast filter (not a white wash), casts a **downward** shadow
(offset 14px down, blur 12, 30% black — not a glow halo around the card), and
a faint glare sweeps in from the upper-right corner once (the classic Steam
shimmer). No outline/glow ring.

The popup is a child of the scroll *viewport* (not the card or its host) so
the lifted art overflows the card's and host's bounds, and `_place()` clamps
it fully inside the viewport so nothing clips at the window edge. It is
transparent to mouse events so the card underneath stays interactive.
"""
from __future__ import annotations
import math
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap, QTransform, QLinearGradient
from PySide6.QtWidgets import QWidget

from forager.ui.theme import C

_SCALE = 1.05
_TRANSITION_MS = 200
_SHADOW_ALPHA = 0.45
_SHADOW_BLUR = 12
_SHADOW_OFFSET = (0, 14)
_SHADOW_ROOM = 36
_SHADOW_SIDE = 8
_EDGE_INSET = 6
_TILT_DEG = 3.0
_PERSPECTIVE = 1000.0
_LIFT = 15.0
_BRIGHTNESS = 1.1
_CONTRAST = 0.95
_GLARE_PEAK = 26
_GLARE_START = -0.15
_GLARE_END = 1.15
_GLARE_WIDTH = 0.12
_RADIUS = C.RADIUS


def _steam_filter(pix: QPixmap) -> QPixmap:
    """Apply Steam's ``brightness(1.1) contrast(0.95)`` per-pixel.

    Runs at capture time (once per show/refresh), so the hover itself stays
    cheap. Uses a 256-entry lookup table over the raw bytes.
    """
    img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    lut = [
        int(max(0, min(255, _CONTRAST * (min(255, _BRIGHTNESS * v) - 128) + 128)))
        for v in range(256)
    ]
    data = img.bits().cast("B")
    for i in range(0, len(data), 4):
        data[i] = lut[data[i]]
        data[i + 1] = lut[data[i + 1]]
        data[i + 2] = lut[data[i + 2]]
    return QPixmap.fromImage(img)


def _shadow_pixmap(w: int, h: int) -> QPixmap:
    """Steam's ``0 14px 12px rgba(0,0,0,.3)`` as a blurred silhouette.

    Rendered once per capture with PIL's C-backed GaussianBlur (Pillow is an
    existing hard dependency), so the hover loop only draws a pixmap.
    """
    from PIL import Image, ImageDraw, ImageFilter

    pad = _SHADOW_BLUR + 6
    sw, sh = w + 2 * pad, h + 2 * pad
    img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        (pad, pad, pad + w - 1, pad + h - 1), radius=_RADIUS, fill=(0, 0, 0, 255)
    )
    img = img.filter(ImageFilter.GaussianBlur(_SHADOW_BLUR))
    qimg = QImage(img.tobytes("raw", "RGBA"), sw, sh, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)

class CardHoverPopup(QWidget):
    """Overlay that lifts one card with Steam's tilt/brighten/down-shadow."""

    def __init__(self, viewport: QWidget, parent=None):
        super().__init__(viewport)
        self._card = None
        self._base: QPixmap | None = None
        self._steam: QPixmap | None = None
        self._shadow: QPixmap | None = None
        self._cx = 0.5
        self._cy = 0.5
        self._progress = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(_TRANSITION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_progress)
        self.hide()

    def _set_progress(self, value):
        self._progress = float(value)
        self.update()

    def show_for(self, card):
        """Capture *card*, lift it over the card (viewport coords)."""
        self._card = card
        w, h = card.width(), card.height()
        base = QPixmap(w, h)
        card.render(base)
        self._base = base
        self._steam = _steam_filter(base)
        self._shadow = _shadow_pixmap(w, h)
        self._place()
        self.raise_()
        self.show()
        self._anim.stop()
        self._anim.setStartValue(self._progress if self._progress > 0 else 0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _place(self):
        """Position over the card in viewport coords, clamped so nothing clips.

        The popup keeps the card exactly where it sits on the grid, extending
        only *downward* by ``_SHADOW_ROOM`` (plus a little side room) so the
        downward Steam shadow has space to render. When the card sits near a
        viewport edge the geometry would hang outside and get clipped, so it
        is clamped (with a small inset) to stay fully visible.
        """
        if self._card is None:
            return
        w, h = self._card.width(), self._card.height()
        nw = int(round(w * _SCALE))
        nh = int(round(h * _SCALE))
        pw = nw + 2 * _SHADOW_SIDE
        ph = nh + _SHADOW_ROOM
        viewport = self.parentWidget()
        p = self._card.mapTo(viewport, QPoint(0, 0))
        x = p.x() - (pw - w) // 2
        y = p.y() - (nh - h) // 2
        x = max(_EDGE_INSET, min(x, viewport.width() - pw - _EDGE_INSET))
        y = max(_EDGE_INSET, min(y, viewport.height() - ph - _EDGE_INSET))
        self.setGeometry(x, y, pw, ph)
        self._cx = nw / 2.0
        self._cy = nh / 2.0

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
        self._steam = None
        self._shadow = None
        self._progress = 0.0
        self.hide()

    def _lift_transform(self, cx: float, cy: float) -> QTransform:
        """Compose Steam's ``rotateX(3deg) translateZ(15px)`` perspective.

        ``translateZ`` → uniform scale ``s = p/(p - lift)``; ``rotateX`` → the
        projective matrix that keeps the top edge farther (smaller) and the
        bottom edge nearer (larger) under a camera ``p`` px away.
        """
        s = _PERSPECTIVE / (_PERSPECTIVE - _LIFT)
        rad = math.radians(_TILT_DEG)
        proj = QTransform(
            1.0, 0.0, 0.0,
            0.0, math.cos(rad), -math.sin(rad) / _PERSPECTIVE,
            0.0, 0.0, 1.0,
        )
        tr = QTransform()
        tr.translate(cx, cy)
        tr = tr * proj
        tr = tr * QTransform(s, 0.0, 0.0, 0.0, s, 0.0, 0.0, 0.0, 1.0)
        tr.translate(-cx, -cy)
        return tr

    def paintEvent(self, event):
        if self._base is None or self._base.isNull():
            return
        a = self._progress
        w, h = self._base.width(), self._base.height()
        cx, cy = self._cx, self._cy
        rect = QRect(int(cx - w / 2), int(cy - h / 2), w, h)
        rectf = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setTransform(self._lift_transform(cx, cy))

        if a > 0.0 and self._shadow is not None and not self._shadow.isNull():
            pad = _SHADOW_BLUR + 6
            offx, offy = _SHADOW_OFFSET
            srect = QRect(rect.x() - pad + offx, rect.y() - pad + offy,
                          self._shadow.width(), self._shadow.height())
            p.setOpacity(a * _SHADOW_ALPHA)
            p.drawPixmap(srect, self._shadow)
            p.setOpacity(1.0)

        clip = QPainterPath()
        clip.addRoundedRect(rectf, _RADIUS, _RADIUS)
        p.setClipPath(clip)

        p.drawPixmap(rect, self._base)
        if a > 0.0:
            p.setOpacity(a)
            p.drawPixmap(rect, self._steam)
            p.setOpacity(1.0)
            self._paint_glare(p, rect, a)
        p.resetTransform()

    def _paint_glare(self, p: QPainter, rect: QRect, a: float):
        """Steam's shimmer: a faint band sweeping in from the upper-right.

        The band travels along the top-right → bottom-left diagonal once per
        hover, then fades out (so the settled state is the uniform brightness
        lift), clipped to the cover's rounded corners.
        """
        if a <= 0.0 or a >= 1.0:
            return
        pos = _GLARE_START + (_GLARE_END - _GLARE_START) * a
        peak = int(round(_GLARE_PEAK * 4.0 * a * (1.0 - a)))
        lo = min(1.0, max(0.0, pos - _GLARE_WIDTH))
        mid = min(1.0, max(0.0, pos))
        hi = min(1.0, max(0.0, pos + _GLARE_WIDTH))
        grad = QLinearGradient(rect.topRight(), rect.bottomLeft())
        grad.setColorAt(lo, QColor(255, 255, 255, 0))
        grad.setColorAt(mid, QColor(255, 255, 255, peak))
        grad.setColorAt(hi, QColor(255, 255, 255, 0))
        p.fillRect(rect, grad)
