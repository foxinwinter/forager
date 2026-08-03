"""Prototype Store page.

A SpaceTheme-style top tab switcher (mirrors ``store/home.css`` "New &
Trending / Top Sellers" tab row) with one tab per storefront. Purely visual
for now: tabs switch between empty placeholder panes, no store is wired up.
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QButtonGroup, QStackedWidget,
    QVBoxLayout, QHBoxLayout,
)

from forager.ui.fonts import UI_FONT
from forager.ui.theme import C, TAB_QSS

_STORES = ("Steam", "Epic Games", "GOG", "itch.io")


class StorePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {C.BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        header = QLabel("Store")
        header.setFont(QFont(UI_FONT, 22, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        layout.addWidget(header)

        self._stack = QStackedWidget()
        for name in _STORES:
            self._stack.addWidget(self._placeholder(name))
        layout.addWidget(self._build_tabs())
        layout.addWidget(self._stack, stretch=1)

    def _build_tabs(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background-color: {C.COLOR_2}; border-radius: {C.RADIUS}px;"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(6, 6, 6, 6)
        bar_layout.setSpacing(6)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, name in enumerate(_STORES):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(TAB_QSS)
            group.addButton(btn, index)
            bar_layout.addWidget(btn)
        self._tabs_group = group
        self._tabs_group.buttonClicked.connect(self._switch_tab)
        group.button(0).setChecked(True)
        return bar

    def _switch_tab(self, button: QPushButton):
        index = self._tabs_group.id(button)
        if index >= 0:
            self._stack.setCurrentIndex(index)

    def _placeholder(self, name: str) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        v = QVBoxLayout(page)
        v.addStretch(1)
        store = QLabel(name)
        store.setAlignment(Qt.AlignmentFlag.AlignCenter)
        store.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 22px; font-weight: 700;"
            f"background: transparent;"
        )
        note = QLabel("Store integration coming soon")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 13px; background: transparent;"
        )
        v.addWidget(store)
        v.addWidget(note)
        v.addStretch(1)
        return page
