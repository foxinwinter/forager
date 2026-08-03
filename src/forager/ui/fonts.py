"""Bundled UI font.

SpaceTheme's default UI font is Be Vietnam Pro; forager bundles the static
OFL-licensed weights used by the QSS (300/400/500/600/700/800) so the launcher
matches the theme without a network dependency.
"""
from __future__ import annotations
from PySide6.QtGui import QFontDatabase

from forager.core.paths import resources_dir

UI_FONT = "Be Vietnam Pro"
_WEIGHT_FILES = (
    "BeVietnamPro-Light.ttf",
    "BeVietnamPro-Regular.ttf",
    "BeVietnamPro-Medium.ttf",
    "BeVietnamPro-SemiBold.ttf",
    "BeVietnamPro-Bold.ttf",
    "BeVietnamPro-ExtraBold.ttf",
)
_registered = False


def register_ui_font() -> str:
    """Register the bundled Be Vietnam Pro weights and return the family name.

    Called at app startup before the theme is applied so the app font and QSS
    ``font-family`` resolve to the bundled family. Falls back to the family
    name when the files are missing (so tests and workers never crash).
    """
    global _registered
    if not _registered:
        fonts_dir = resources_dir() / "fonts"
        for name in _WEIGHT_FILES:
            path = fonts_dir / name
            if path.is_file():
                try:
                    QFontDatabase.addApplicationFont(str(path))
                except Exception:
                    pass
        _registered = True
    return UI_FONT
