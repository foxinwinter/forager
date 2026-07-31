from __future__ import annotations
from PySide6.QtCore import Qt, QSize, Signal, QFile
from PySide6.QtGui import QIcon, QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QStyle, QFrame,
    QInputDialog, QMessageBox,
)

from forager.core.game import Game, Source
from forager.library.icon_provider import load_icon
from forager.ui.theme import C

_SIDEBAR_W = 240


def source_icon(src: Source, size=16) -> QIcon:
    paths = {
        Source.STEAM: "/usr/share/icons/hicolor/32x32/apps/steam.png",
        Source.MINECRAFT: "/usr/share/icons/Papirus/32x32/apps/minecraft.svg",
        Source.STANDALONE: "/usr/share/icons/breeze/mimetypes/22/application-x-executable.svg",
    }
    path = paths.get(src)
    if path and QFile.exists(path):
        icon = QIcon(path)
        if not icon.isNull():
            return icon
    icon = QIcon.fromTheme({
        Source.STEAM: "steam",
        Source.MINECRAFT: "minecraft",
        Source.STANDALONE: "application-x-executable",
    }.get(src, ""))
    if not icon.isNull():
        return icon
    return QIcon.fromTheme("applications-games")


class Sidebar(QWidget):
    home_requested = Signal()
    game_selected = Signal(object)
    source_changed = Signal(object)
    search_changed = Signal(str)
    update_proton_requested = Signal()
    settings_requested = Signal()
    token_set = Signal()

    _FILTERS = [
        (None, "All Games"),
        (Source.STEAM, "Steam"),
        (Source.MINECRAFT, "Minecraft"),
        (Source.STANDALONE, "Standalone"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._games: list[Game] = []
        self._current_source: Source | None = None
        self._search_text = ""
        self._buttons: list[QPushButton] = []

        self.setFixedWidth(_SIDEBAR_W)
        self.setStyleSheet(f"background-color: {C.COLOR_2};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        self._build_home(layout)
        self._build_filters(layout)
        self._build_search(layout)
        self._build_list(layout)
        self._build_user_panel(layout)

    def _build_home(self, layout):
        self._home_btn = QPushButton("Home")
        self._home_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {C.COLOR_1}; color: {C.TEXT};
                border: none; border-radius: {C.RADIUS}px;
                padding: 10px 12px; font-size: 13px; font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{ background-color: {C.COLOR_3}; }}
            """
        )
        self._home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_btn.clicked.connect(self.home_requested)
        layout.addWidget(self._home_btn)

    def _build_filters(self, layout):
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 8, 4, 0)
        header_layout.setSpacing(4)

        label = QLabel("LIBRARY")
        label.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 11px; font-weight: 700;"
            f"letter-spacing: 1px;"
        )
        header_layout.addWidget(label)
        header_layout.addStretch(1)

        settings_btn = QPushButton("⚙")
        settings_btn.setToolTip("Settings")
        settings_btn.setFixedSize(26, 22)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C.TEXT_DIM}; border: none;"
            f"border-radius: 4px; font-size: 13px; padding: 0; }}"
            f"QPushButton:hover {{ color: {C.TEXT}; }}"
        )
        settings_btn.clicked.connect(self.settings_requested)
        header_layout.addWidget(settings_btn)

        layout.addWidget(header)

        for src, text in self._FILTERS:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._filter_style())
            if src is None:
                btn.setChecked(True)
            if src is not None:
                btn.setIcon(source_icon(src, 14))
            btn.clicked.connect(lambda _=False, s=src: self._set_filter(s))
            layout.addWidget(btn)
            self._buttons.append(btn)

    def _filter_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {C.COLOR_3}; color: {C.TEXT_MUTED};
                border: none; border-radius: {C.RADIUS}px;
                padding: 7px 10px; font-size: 13px; text-align: left;
            }}
            QPushButton:hover {{ background-color: {C.COLOR_1}; color: {C.TEXT}; }}
            QPushButton:checked {{
                background-color: {C.COLOR_1}; color: {C.ACCENT_1}; font-weight: 600;
            }}
        """

    def _set_filter(self, src: Source | None):
        self._current_source = src
        for btn, (s, _) in zip(self._buttons, self._FILTERS):
            btn.setChecked(s is src)
        self._rebuild_list()
        self.source_changed.emit(src)

    def _build_search(self, layout):
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search games...")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet(
            f"QLineEdit {{ background-color: {C.COLOR_3}; border: none;"
            f"border-radius: {C.RADIUS}px; padding: 7px 12px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border: 1px solid {C.ACCENT_1}; }}"
        )
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

    def _on_search(self, text: str):
        self._search_text = text.strip().lower()
        self._rebuild_list()
        self.search_changed.emit(self._search_text)

    def _build_list(self, layout):
        self._list = QListWidget()
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setIconSize(QSize(22, 22))
        self._list.setSpacing(4)
        self._list.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent; border: none; outline: none;
                padding-top: 4px; font-size: 12px;
            }}
            QListWidget::item {{
                padding: 3px 8px; border-radius: {C.RADIUS}px;
                color: {C.TEXT_MUTED};
            }}
            QListWidget::item:hover {{
                background-color: {C.COLOR_3}; color: {C.TEXT};
            }}
            QListWidget::item:selected {{
                background-color: rgba(102, 108, 255, 90);
                color: {C.ACCENT_2};
            }}
            """
        )
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self._list, stretch=1)

    def _on_selection_changed(self):
        item = self._list.currentItem()
        if item is None:
            return
        game: Game = item.data(Qt.ItemDataRole.UserRole)
        if game is not None:
            self.game_selected.emit(game)

    def _on_double_clicked(self, item: QListWidgetItem):
        game: Game | None = item.data(Qt.ItemDataRole.UserRole)
        if game is not None:
            self.game_selected.emit(game)

    def _build_user_panel(self, layout):
        panel = QFrame()
        panel.setStyleSheet(
            f"background-color: {C.COLOR_3}; border: none; border-radius: {C.RADIUS}px;"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(8)

        self._count_label = QLabel()
        self._count_label.setStyleSheet(f"color: {C.TEXT_MUTED}; font-size: 12px;")
        panel_layout.addWidget(self._count_label)

        update_btn = QPushButton("Update Proton")
        update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        update_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {C.COLOR_1}; color: {C.TEXT}; border: none;
                border-radius: {C.RADIUS}px; padding: 7px 10px; font-size: 12px;
                font-weight: 600; text-align: center;
            }}
            QPushButton:hover {{ background-color: {C.COLOR_4}; color: {C.ACCENT_2}; }}
            QPushButton:disabled {{ color: {C.TEXT_DIM}; }}
            """
        )
        update_btn.clicked.connect(self.update_proton_requested)
        panel_layout.addWidget(update_btn)

        token_btn = QPushButton("SGDB Token")
        token_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        token_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {C.COLOR_1}; color: {C.TEXT}; border: none;
                border-radius: {C.RADIUS}px; padding: 7px 10px; font-size: 12px;
                font-weight: 600; text-align: center;
            }}
            QPushButton:hover {{ background-color: {C.COLOR_4}; color: {C.ACCENT_2}; }}
            """
        )
        token_btn.clicked.connect(self._set_token)
        panel_layout.addWidget(token_btn)

        layout.addWidget(panel)

    def _set_token(self):
        from forager.library.steamgriddb import get_api_key, set_api_key

        current = get_api_key() or ""
        text, ok = QInputDialog.getText(
            self, "SteamGridDB Token",
            "Enter your SteamGridDB API token\n(kept in the system keyring, not stored in plaintext):",
            QLineEdit.EchoMode.Password, current,
        )
        if not ok or not text.strip():
            return
        try:
            set_api_key(text.strip())
        except Exception as e:
            QMessageBox.warning(self, "Token Error", f"Could not save token:\n{e}")
            return
        self.token_set.emit()

    def set_games(self, games: list[Game]):
        self._games = sorted(games, key=lambda g: (g.sort_key or g.name).lower())
        self._rebuild_list()

    def _rebuild_list(self):
        current = self._list.currentItem()
        keep = None
        if current is not None:
            keep = current.data(Qt.ItemDataRole.UserRole)

        self._list.blockSignals(True)
        self._list.clear()
        shown = 0
        for g in self._games:
            if self._current_source is not None and g.source != self._current_source:
                continue
            if self._search_text and self._search_text not in g.name.lower():
                continue
            item = QListWidgetItem()
            item.setText(g.name.replace("/", " / "))
            item.setData(Qt.ItemDataRole.UserRole, g)
            item.setToolTip(str(g.path))
            icon = load_icon(g, allow_network=False)
            if icon is not None:
                item.setIcon(QIcon(icon))
            else:
                item.setIcon(source_icon(g.source, 16))
            self._list.addItem(item)
            if keep is not None and g == keep:
                self._list.setCurrentItem(item)
            shown += 1

        if keep is None and self._list.count():
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)

        total = len([g for g in self._games if self._current_source is None or g.source == self._current_source])
        self._count_label.setText(f"{shown} of {total} games")

    def set_icon(self, game: Game, icon: QIcon):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == game:
                item.setIcon(icon)
                return

    def select_game(self, game: Game):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == game:
                self._list.setCurrentItem(item)
                return

    def focus_next(self, direction: int):
        row = self._list.currentRow() + direction
        if 0 <= row < self._list.count():
            self._list.setCurrentRow(row)
            return True
        return False

    def activate_current(self):
        item = self._list.currentItem()
        if item is not None:
            self._on_selection_changed()
            return True
        return False
