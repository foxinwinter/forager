"""The scrollable card grid shown on the Library home page.

Owns the fixed-size portrait ``GameCard`` tiles, the adaptive column layout
(search-filtered, sorted), and keyboard/gamepad focus. Art tiles load
synchronously from local/cached sources here; network art is delivered later
by the worker thread and applied through :meth:`set_card_art`.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QScrollArea

from forager.core.game import Game
from forager.services import art
from forager.ui.theme import C
from forager.ui.game_card import GameCard

_GRID_MARGIN = 23
_GRID_MIN_GAP = 12
_GRID_V_GAP = 16


class GameGrid(QWidget):
    card_clicked = Signal(object)
    card_activated = Signal(object)

    def __init__(self, card_w: int, card_h: int, parent=None):
        super().__init__(parent)
        self._games: list[Game] = []
        self._cards: list[GameCard] = []
        self._card_index = 0
        self._card_w, self._card_h = card_w, card_h
        self._search_text = ""

        self.setStyleSheet("background: transparent;")
        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self._empty_label = QLabel("No games found.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 14px; background: transparent; padding: 60px;"
        )
        v.addWidget(self._empty_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"QScrollArea {{ background: {C.BG}; border: none; }}")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.viewport().installEventFilter(self)

        self._grid_host = QWidget()
        self._grid_host.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_host)
        v.addWidget(self._scroll, stretch=1)

    # -- public API -----------------------------------------------------

    def set_games(self, games: list[Game]):
        self._games = games
        self._rebuild_cards()

    def set_search(self, text: str):
        self._search_text = text
        self._rebuild_cards()

    def set_card_size(self, card_w: int, card_h: int):
        self._card_w, self._card_h = card_w, card_h
        for card in self._cards:
            card.setFixedSize(card_w, card_h)
        self._relayout_cards()

    def cards(self) -> list[GameCard]:
        return self._cards

    def count(self) -> int:
        return len(self._cards)

    def current_index(self) -> int:
        return self._card_index

    def card_at(self, index: int) -> GameCard | None:
        if 0 <= index < len(self._cards):
            return self._cards[index]
        return None

    def game_at(self, index: int) -> Game | None:
        card = self.card_at(index)
        return card.game if card is not None else None

    def column_count(self) -> int:
        return self._grid.columnCount()

    def viewport(self):
        return self._scroll.viewport()

    def focus_index(self, index: int):
        if not self._cards:
            return
        index = max(0, min(len(self._cards) - 1, index))
        for i, card in enumerate(self._cards):
            card.set_focused(i == index)
        self._card_index = index
        self._scroll.ensureWidgetVisible(self._cards[index], 40, 40)

    def set_card_art(self, game: Game, pix):
        for card in self._cards:
            if card.game == game:
                card.set_art(pix)
                return

    # -- internals ------------------------------------------------------

    def _filtered_games(self) -> list[Game]:
        out = []
        for g in self._games:
            if self._search_text and self._search_text not in g.name.lower():
                continue
            out.append(g)
        out.sort(key=lambda g: (g.sort_key or g.name).lower())
        return out

    def _rebuild_cards(self):
        for card in self._cards:
            self._grid.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._card_index = 0

        for game in self._filtered_games():
            card = GameCard(game, card_w=self._card_w, card_h=self._card_h)
            card.clicked.connect(self.card_clicked)
            card.activated.connect(self.card_activated)
            self._cards.append(card)

        self._empty_label.setVisible(len(self._cards) == 0)
        self._scroll.setVisible(len(self._cards) > 0)
        self._relayout_cards()
        self._load_card_art()

    def _load_card_art(self):
        for card in self._cards:
            card.set_art(art.load_grid(card.game, allow_network=False))

    def _relayout_cards(self):
        if not self._cards:
            return
        for i in reversed(range(self._grid.count())):
            widget = self._grid.itemAt(i).widget()
            if widget is not None:
                self._grid.removeWidget(widget)

        viewport_w = self._scroll.viewport().width()
        scrollbar = self._scroll.verticalScrollBar()
        if scrollbar is not None:
            viewport_w -= scrollbar.sizeHint().width()

        avail = max(1, viewport_w - 2 * _GRID_MARGIN)
        cols = max(1, (avail + _GRID_MIN_GAP) // (self._card_w + _GRID_MIN_GAP))
        cols = min(cols, len(self._cards))

        used = cols * self._card_w + (cols - 1) * _GRID_MIN_GAP
        remaining = avail - used
        if cols > 1 and remaining > 0:
            gap = _GRID_MIN_GAP + remaining // (cols - 1)
        else:
            gap = _GRID_MIN_GAP

        self._grid.setContentsMargins(_GRID_MARGIN, 0, _GRID_MARGIN, 0)
        self._grid.setHorizontalSpacing(gap)
        self._grid.setVerticalSpacing(_GRID_V_GAP)

        old_cols = getattr(self, "_layout_cols", 0)
        for col in range(max(old_cols, cols)):
            self._grid.setColumnStretch(col, 0)
        self._layout_cols = cols

        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // cols, i % cols)

    def eventFilter(self, obj, event):
        if obj is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._relayout_cards()
        return super().eventFilter(obj, event)
