from __future__ import annotations

import re
import threading
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from forager.ui.theme import C

RESOURCE_DIR = Path(__file__).resolve().parents[3] / "resources" / "icons"

_CURRENT_COLOR = re.compile(r'(stroke|fill)="currentColor"')

_cache: dict[tuple[str, str], QIcon] = {}
_lock = threading.Lock()


def load_icon(name: str, color: str | None = None) -> QIcon:
    """Load a bundled Iconoir SVG recolored for the theme.

    Iconoir ships single-color line icons using ``currentColor`` (regular icons
    as ``stroke="currentColor"``, solid icons as ``fill="currentColor"``). Qt
    renders ``currentColor`` as black, so it is replaced with the requested
    color here. Pass a light color (e.g. ``C.TEXT``) for dark UIs and a dark
    color (e.g. ``C.BG``) for light UIs. Icons are cached per (name, color)
    and shared across threads.
    """
    color = color or C.TEXT
    key = (name, color.lower())
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached

    path = RESOURCE_DIR / f"{name}.svg"
    if not path.is_file():
        return QIcon()

    svg = path.read_text("utf-8", errors="replace")
    svg = _CURRENT_COLOR.sub(lambda m: f'{m.group(1)}="{color}"', svg)

    renderer = QSvgRenderer()
    if not renderer.load(svg.encode("utf-8")):
        return QIcon()

    pixmap = QPixmap(renderer.defaultSize())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pixmap)
    with _lock:
        _cache[key] = icon
    return icon
