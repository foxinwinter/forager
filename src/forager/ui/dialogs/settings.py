"""Settings dialog — Steam-style sidebar navigation over a stacked page,
mirroring SpaceTheme's settings layout (nav items + panelled content).
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QButtonGroup, QDialogButtonBox, QWidget, QFrame, QLabel,
)

from forager.core.config import settings
from forager.ui.theme import C, PAGE_BG
from forager.ui.icons import load_icon as load_bundled_icon
from forager.ui.dialogs.account_tab import AccountTab
from forager.ui.dialogs.settings_tabs import LibraryTab, ProtonTab, DISPLAY_SIZES

_NAV_PANEL_QSS = f"""
QFrame#SettingsNav {{
    background-color: {C.COLOR_2};
    border: none;
    border-radius: {C.RADIUS}px;
}}
"""

_NAV_BTN_QSS = f"""
QPushButton {{
    background: transparent;
    color: #b8bcbf;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 6px;
    padding: 9px 12px;
    padding-left: 13px;
    font-size: 13px;
    text-align: left;
}}
QPushButton:hover {{
    color: {C.TEXT};
    background-color: {C.COLOR_3};
}}
QPushButton:checked {{
    color: {C.ACCENT_1};
    background-color: {C.COLOR_3};
    font-weight: 600;
    border-left: 3px solid {C.ACCENT_1};
    padding-left: 10px;
}}
"""

_CONTENT_PANEL_QSS = f"""
QFrame#SettingsContent {{
    background-color: {C.COLOR_2};
    border: none;
    border-radius: {C.RADIUS}px;
}}
"""

_BUTTONS_QSS = f"""
QPushButton {{
    background-color: {C.COLOR_2};
    color: {C.TEXT};
    border: 1px solid {C.COLOR_3};
    border-radius: {C.RADIUS}px;
    padding: 0 18px;
    min-height: 32px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {C.COLOR_3};
}}
QPushButton#saveButton {{
    background-color: {C.ACCENT_1};
    color: {C.TEXT};
    border: none;
}}
QPushButton#saveButton:hover {{
    background-color: {C.ACCENT_2};
}}
"""

_HEADER_QSS = f"""
QFrame#SettingsHeader {{
    background-color: {C.COLOR_1};
    border-bottom: 1px solid {C.COLOR_3};
}}
"""


def resolve_card_size(key: str) -> tuple[int, int]:
    for k, _label, w, h in DISPLAY_SIZES:
        if k == key:
            return (w, h)
    return (165, 248)


def _nav_icon(name: str) -> QIcon:
    off = load_bundled_icon(name, "#b8bcbf").pixmap(18, 18)
    on = load_bundled_icon(name, C.ACCENT_1).pixmap(18, 18)
    icon = QIcon()
    icon.addPixmap(off, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(on, QIcon.Mode.Normal, QIcon.State.On)
    return icon


class SettingsDialog(QDialog):
    update_proton_requested = Signal()
    games_dir_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(760, 560)
        self.setMinimumSize(640, 500)
        self.setStyleSheet(f"#SettingsDialog {{ background: {PAGE_BG}; }}")
        self.setObjectName("SettingsDialog")

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 12)
        body.setSpacing(16)
        body.addWidget(self._build_nav())

        self._library = LibraryTab()
        self._proton = ProtonTab()
        self._account = AccountTab()

        self._pages = QStackedWidget()
        for tab in (self._library, self._proton, self._account):
            self._pages.addWidget(tab)
        content = QFrame()
        content.setObjectName("SettingsContent")
        content.setStyleSheet(_CONTENT_PANEL_QSS)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.addWidget(self._pages)
        body.addWidget(content, stretch=1)

        v.addLayout(body)
        v.addWidget(self._build_footer())

        self._proton.update_proton_requested.connect(self.update_proton_requested)

    # -- shell pieces --------------------------------------------------

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("SettingsHeader")
        header.setStyleSheet(_HEADER_QSS)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(load_bundled_icon("settings", C.ACCENT_1).pixmap(20, 20))
        lay.addWidget(icon)

        title = QLabel("Settings")
        title.setFont(QFont("Roboto", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.ACCENT_1}; background: transparent;")
        lay.addWidget(title)

        subtitle = QLabel("Library, Proton and account")
        subtitle.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 12px; background: transparent;")
        lay.addWidget(subtitle)
        lay.addStretch(1)
        return header

    def _build_nav(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SettingsNav")
        panel.setStyleSheet(_NAV_PANEL_QSS)
        panel.setFixedWidth(190)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        group = QButtonGroup(self)
        group.setExclusive(True)
        self._page_order = []
        first = True
        for label, icon in (
            ("Library", "folder"),
            ("Proton", "shield"),
            ("Account", "user"),
        ):
            btn = QPushButton(label)
            btn.setIcon(_nav_icon(icon))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            btn.setChecked(first)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(_NAV_BTN_QSS)
            group.addButton(btn)
            lay.addWidget(btn)
            self._page_order.append(label)
            first = False
        group.buttonClicked.connect(
            lambda btn: self._pages.setCurrentIndex(self._page_order.index(btn.text()))
        )
        lay.addStretch(1)
        return panel

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("SettingsFooter")
        footer.setStyleSheet(
            f"QFrame#SettingsFooter {{ border-top: 1px solid {C.COLOR_3}; background: transparent; }}"
        )
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(20, 12, 20, 14)
        lay.setSpacing(10)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(_BUTTONS_QSS)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setObjectName("saveButton")
        save_btn.setText("Save")
        save_btn.setIcon(load_bundled_icon("floppy-disk", C.TEXT))
        save_btn.setIconSize(QSize(14, 14))
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Cancel")
        cancel_btn.setIcon(load_bundled_icon("xmark", C.TEXT_DIM))
        cancel_btn.setIconSize(QSize(14, 14))
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        lay.addStretch(1)
        lay.addWidget(buttons)
        return footer

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
