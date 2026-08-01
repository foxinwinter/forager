"""The top bar: forager menu, back/forward buttons, and the gamepad hint."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QApplication, QToolButton, QMenu,
    QButtonGroup,
)

from forager.ui.theme import C, NAV_TAB_QSS
from forager.ui.icons import load_icon as load_bundled_icon


class TitleBar(QWidget):
    settings_requested = Signal()
    update_proton_requested = Signal()
    test_download_requested = Signal()
    run_updates_requested = Signal()
    back_requested = Signal()
    store_tab_requested = Signal()
    library_tab_requested = Signal()

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

        self._tabs = self._build_tabs()
        lay.addWidget(self._tabs, 0, Qt.AlignmentFlag.AlignCenter)

        lay.addStretch(1)

        self._update_pill = QPushButton()
        self._update_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_pill.setStyleSheet(
            f"QPushButton {{ color: {C.YELLOW}; background: transparent;"
            f"border: 1px solid {C.YELLOW}; border-radius: {C.RADIUS}px;"
            f"padding: 4px 10px; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
        )
        self._update_pill.hide()
        self._update_pill.clicked.connect(self.run_updates_requested)
        lay.addWidget(self._update_pill)

        self._controller_hint = QLabel("")
        self._controller_hint.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent; padding: 4px 8px;"
        )
        lay.addWidget(self._controller_hint)

    def _build_tabs(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        group = QButtonGroup(self)
        group.setExclusive(True)
        self._store_tab = self._tab_button("Store", group, self.store_tab_requested)
        self._library_tab = self._tab_button("Library", group, self.library_tab_requested)
        lay.addWidget(self._store_tab)
        lay.addWidget(self._library_tab)
        self._tabs_group = group
        self._library_tab.setChecked(True)
        return bar

    def _tab_button(self, text: str, group: QButtonGroup, signal) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(NAV_TAB_QSS)
        btn.clicked.connect(signal)
        group.addButton(btn)
        return btn

    def set_active_tab(self, name: str) -> None:
        if name == "store":
            self._store_tab.setChecked(True)
        else:
            self._library_tab.setChecked(True)

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

    def set_updates(self, outdated: list[str]) -> None:
        if not outdated:
            self._update_pill.hide()
            return
        n = len(outdated)
        self._update_pill.setText(f"{n} update{'s' if n != 1 else ''} available")
        self._update_pill.setToolTip("Updates ready: " + ", ".join(outdated))
        self._update_pill.show()
