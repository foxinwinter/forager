"""The top bar: forager menu, back/forward buttons, and the gamepad hint."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QApplication, QToolButton, QMenu,
)

from forager.ui.theme import C
from forager.ui.icons import load_icon as load_bundled_icon


class TitleBar(QWidget):
    settings_requested = Signal()
    update_proton_requested = Signal()
    test_download_requested = Signal()
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(
            f"background-color: {C.COLOR_1}; border-bottom: 1px solid {C.COLOR_3};"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        logo = QToolButton()
        logo.setText("forager")
        logo.setFont(QFont("Roboto", 16, QFont.Weight.Bold))
        logo.setCursor(Qt.CursorShape.PointingHandCursor)
        logo.setToolTip("forager menu")
        logo.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        logo.setStyleSheet(
            f"QToolButton {{ color: {C.ACCENT_1}; background: transparent; border: none;"
            f"border-radius: {C.RADIUS}px; padding: 6px 10px; }}"
            f"QToolButton:hover {{ background-color: {C.COLOR_3}; }}"
            f"QToolButton::menu-indicator {{ image: none; }}"
        )
        self._main_menu = QMenu(self)
        self._main_menu.addAction("Settings…", self.settings_requested.emit)
        self._main_menu.addAction("Update Proton", self.update_proton_requested.emit)
        self._main_menu.addSeparator()
        self._main_menu.addAction("Test Download…", self.test_download_requested.emit)
        self._main_menu.addSeparator()
        self._main_menu.addAction("Quit", QApplication.instance().quit)
        logo.setMenu(self._main_menu)
        lay.addWidget(logo)

        self._back_btn = self._nav_button("arrow-left")
        self._forward_btn = self._nav_button("arrow-right")
        self._back_btn.setToolTip("Back to Library")
        self._forward_btn.setToolTip("Forward")
        self._back_btn.clicked.connect(self.back_requested)
        self._forward_btn.setEnabled(False)
        lay.addWidget(self._back_btn)
        lay.addWidget(self._forward_btn)

        lay.addStretch(1)

        self._controller_hint = QLabel("")
        self._controller_hint.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent; padding: 4px 8px;"
        )
        lay.addWidget(self._controller_hint)

    def _nav_button(self, icon_name: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setIcon(load_bundled_icon(icon_name, C.TEXT))
        btn.setIconSize(QSize(18, 18))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {C.COLOR_2}; border: none;
                border-radius: {C.RADIUS}px;
            }}
            QPushButton:hover {{ background-color: {C.COLOR_3}; }}
            """
        )
        return btn

    def set_back_enabled(self, enabled: bool):
        self._back_btn.setEnabled(enabled)

    def set_controller_hint(self, text: str):
        self._controller_hint.setText(text)
