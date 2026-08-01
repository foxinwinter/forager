from __future__ import annotations
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication


class C:
    """SpaceTheme palette (https://github.com/SpaceTheme/Steam)."""

    BG = "#0a0a0a"
    COLOR_1 = "#111111"
    COLOR_2 = "#1e1e1e"
    COLOR_3 = "#141414"
    COLOR_4 = "#181818"
    COLOR_5 = "#26292c"
    COLOR_6 = "#262629"
    ACCENT_1 = "#666cff"
    ACCENT_2 = "#878cff"
    RED = "#f04a4a"
    RED_HOVER = "#f26363"
    GREEN = "#24a65a"
    GREEN_HOVER = "#27b964"
    BLUE = "#4b89ef"
    BLUE_HOVER = "#649af2"
    YELLOW = "#ef8d4b"
    TEXT = "#ffffff"
    TEXT_DIM = "#8e8e8e"
    TEXT_MUTED = "#a3aab9"

    RADIUS = 8


TAB_QSS = f"""
QPushButton {{
    background-color: {C.COLOR_3};
    color: #a9a9a9;
    border: none;
    border-radius: {C.RADIUS}px;
    padding: 6px 16px;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: {C.COLOR_4};
}}
QPushButton:checked {{
    background-color: {C.COLOR_1};
    color: #ffffff;
}}
"""


def load() -> dict[str, str]:
    return {k: getattr(C, k) for k in dir(C) if k.isupper()}


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")

    font = QFont("Roboto", 10)
    app.setFont(font)

    p = QPalette()
    bg = QColor(C.BG)
    base = QColor(C.COLOR_1)
    surface = QColor(C.COLOR_2)
    alt = QColor(C.COLOR_3)
    fg = QColor(C.TEXT)
    dim = QColor(C.TEXT_DIM)
    accent = QColor(C.ACCENT_1)

    p.setColor(QPalette.ColorRole.Window, bg)
    p.setColor(QPalette.ColorRole.WindowText, fg)
    p.setColor(QPalette.ColorRole.Base, base)
    p.setColor(QPalette.ColorRole.AlternateBase, alt)
    p.setColor(QPalette.ColorRole.Text, fg)
    p.setColor(QPalette.ColorRole.Button, surface)
    p.setColor(QPalette.ColorRole.ButtonText, fg)
    p.setColor(QPalette.ColorRole.BrightText, accent)
    p.setColor(QPalette.ColorRole.Light, QColor(C.COLOR_5))
    p.setColor(QPalette.ColorRole.Dark, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Mid, alt)
    p.setColor(QPalette.ColorRole.Midlight, QColor(C.COLOR_4))
    p.setColor(QPalette.ColorRole.Shadow, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Highlight, accent)
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(C.BG))
    p.setColor(QPalette.ColorRole.Link, accent)
    p.setColor(QPalette.ColorRole.LinkVisited, QColor(C.ACCENT_2))
    p.setColor(QPalette.ColorRole.PlaceholderText, dim)
    p.setColor(QPalette.ColorRole.ToolTipBase, surface)
    p.setColor(QPalette.ColorRole.ToolTipText, fg)

    app.setPalette(p)
    app.setStyleSheet(stylesheet())


def stylesheet() -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {C.BG};
        color: {C.TEXT};
        font-family: Roboto, "DejaVu Sans", sans-serif;
    }}
    QWidget:disabled {{
        color: {C.TEXT_DIM};
    }}

    QLabel {{
        color: {C.TEXT};
        background: transparent;
    }}

    QPushButton {{
        background-color: {C.COLOR_2};
        color: {C.TEXT};
        border: none;
        border-radius: {C.RADIUS}px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {C.COLOR_3};
    }}
    QPushButton:pressed {{
        background-color: {C.COLOR_4};
    }}
    QPushButton:disabled {{
        background-color: {C.COLOR_2};
        color: {C.TEXT_DIM};
    }}
    QPushButton:focus {{
        outline: none;
    }}

    QLineEdit {{
        background-color: {C.COLOR_3};
        color: {C.TEXT};
        border: none;
        border-radius: {C.RADIUS}px;
        padding: 6px 12px;
        font-size: 13px;
        selection-background-color: {C.ACCENT_1};
        selection-color: {C.BG};
    }}
    QLineEdit:focus {{
        border: 1px solid {C.ACCENT_1};
    }}
    QLineEdit::placeholder {{
        color: {C.TEXT_DIM};
    }}

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {C.COLOR_5};
        border-radius: 4px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C.COLOR_6};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {C.COLOR_5};
        border-radius: 4px;
        min-width: 40px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {C.COLOR_6};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QMenu {{
        background-color: {C.COLOR_2};
        color: {C.TEXT};
        border: none;
        border-radius: {C.RADIUS}px;
        padding: 4px;
        font-size: 13px;
    }}
    QMenu::item {{
        padding: 6px 24px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {C.COLOR_3};
    }}

    QToolTip {{
        background-color: {C.COLOR_2};
        color: {C.TEXT};
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
    }}

    QMessageBox {{
        background-color: {C.COLOR_1};
    }}
    QMessageBox QLabel {{
        color: {C.TEXT};
    }}
    QMessageBox QPushButton {{
        min-width: 90px;
    }}

    QFileDialog {{
        background-color: {C.COLOR_1};
    }}
    """
