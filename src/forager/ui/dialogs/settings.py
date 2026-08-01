from __future__ import annotations
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QButtonGroup, QDialogButtonBox,
)

from forager.core.config import settings
from forager.ui.theme import C
from forager.ui.icons import load_icon as load_bundled_icon
from forager.ui.dialogs.account_tab import AccountTab
from forager.ui.dialogs.settings_tabs import LibraryTab, ProtonTab, DISPLAY_SIZES

_NAV_BTN_QSS = f"""
QPushButton {{
    background-color: {C.COLOR_3}; color: {C.TEXT_MUTED};
    border: none; border-radius: {C.RADIUS}px;
    padding: 9px 14px; font-size: 13px; text-align: left;
}}
QPushButton:hover {{ background-color: {C.COLOR_1}; color: {C.TEXT}; }}
QPushButton:checked {{
    background-color: {C.COLOR_1}; color: {C.ACCENT_1}; font-weight: 600;
}}
"""

_BUTTONS_QSS = (
    f"QPushButton {{ background-color: #ffffff; color: #0d0d0d;"
    f" border: none; border-radius: {C.RADIUS}px; padding: 6px 16px; font-weight: 600; }}"
    f"QPushButton:hover {{ background-color: #e6e6e6; }}"
    f"QPushButton:default {{ background-color: #ffffff; color: #0d0d0d; border: none; }}"
)


def resolve_card_size(key: str) -> tuple[int, int]:
    for k, _label, w, h in DISPLAY_SIZES:
        if k == key:
            return (w, h)
    return (165, 248)


class SettingsDialog(QDialog):
    update_proton_requested = Signal()
    games_dir_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(560, 420)
        self.setStyleSheet(f"background-color: {C.BG}; color: {C.TEXT};")

        v = QVBoxLayout(self)
        body = QHBoxLayout()
        body.setSpacing(12)

        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        body.addLayout(self._build_nav(nav_group))

        self._library = LibraryTab()
        self._proton = ProtonTab()
        self._account = AccountTab()

        self._pages = QStackedWidget()
        self._pages.addWidget(self._library)
        self._pages.addWidget(self._proton)
        self._pages.addWidget(self._account)
        body.addWidget(self._pages, stretch=1)

        nav_group.buttonClicked.connect(
            lambda btn: self._pages.setCurrentIndex(self._page_order.index(btn.text()))
        )
        v.addLayout(body)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(_BUTTONS_QSS)
        buttons.button(QDialogButtonBox.StandardButton.Save).setIcon(
            load_bundled_icon("floppy-disk", C.BG)
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setIcon(
            load_bundled_icon("xmark", "#ff5f57")
        )
        for sb in (QDialogButtonBox.StandardButton.Save, QDialogButtonBox.StandardButton.Cancel):
            buttons.button(sb).setIconSize(QSize(14, 14))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        self._proton.update_proton_requested.connect(self.update_proton_requested)

    def _build_nav(self, group: QButtonGroup) -> QVBoxLayout:
        self._page_order = ["Library", "Proton", "Account"]
        nav = QVBoxLayout()
        nav.setSpacing(4)
        first = True
        for label in self._page_order:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(first)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(_NAV_BTN_QSS)
            group.addButton(btn)
            nav.addWidget(btn)
            first = False
        nav.addStretch(1)
        return nav

    # -- accessors read by the main window -----------------------------

    def selected_card_size(self) -> str:
        return self._library.selected_card_size()

    def games_dir_text(self) -> str:
        return self._library.games_dir_text()

    # -- save / close --------------------------------------------------

    def done(self, result):
        self._account.cancel_worker()
        super().done(result)

    def _save(self):
        settings.set("games_dir", self._library.games_dir_text().strip() or str(settings.games_dir))
        settings.set("steam_appcache", self._library.steam_cache_text().strip() or str(settings.steam_appcache))
        settings.set("display_size", self._library.selected_card_size())
        features = settings.data.setdefault("proton", {}).setdefault("features", {})
        features.update(self._proton.feature_values())
        settings.save()
        self._account.save()
        self.accept()
