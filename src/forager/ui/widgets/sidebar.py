from __future__ import annotations
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QFrame,
)

from forager.core.game import Game
from forager.library.icon_provider import load_icon
from forager.ui.theme import C
from forager.ui.icons import load_icon as load_bundled_icon
from forager.ui.pages.downloads import DownloadBox

_SIDEBAR_W = 240


class Sidebar(QWidget):
    game_selected = Signal(object)
    search_changed = Signal(str)
    download_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._games: list[Game] = []
        self._search_text = ""

        self.setFixedWidth(_SIDEBAR_W)
        self.setStyleSheet(f"background-color: {C.COLOR_2};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        self._build_search(layout)
        self._build_list(layout)
        self._build_download_box(layout)
        self._build_user_panel(layout)

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

    def _build_download_box(self, layout):
        self._download_box = DownloadBox()
        self._download_box.clicked.connect(self.download_clicked)
        layout.addWidget(self._download_box)

    def begin_download(self, name: str) -> None:
        self._download_box.begin(name)

    def set_download_progress(self, progress) -> None:
        self._download_box.set_progress(progress)

    def hide_download(self) -> None:
        self._download_box.hide_download()

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

        layout.addWidget(panel)

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
                item.setIcon(load_bundled_icon("box", C.TEXT_MUTED))
            self._list.addItem(item)
            if keep is not None and g == keep:
                self._list.setCurrentItem(item)
            shown += 1

        if keep is None and self._list.count():
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)

        total = len(self._games)
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
