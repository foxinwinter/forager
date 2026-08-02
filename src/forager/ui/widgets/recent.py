"""The "Recently Played" strip shown at the very top of the Library home page.

A fixed (for now) horizontal row of small cards for the games with the most
recent last-played stamp, each with the game name and accumulated playtime
below. It hides while the user is searching, matching how the main grid
filters.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)

from forager.core.game import Game
from forager.library.playtime import PlaytimeStore, format_playtime, game_key
from forager.services import art
from forager.ui.theme import C
from forager.ui.widgets.game_card import GameCard

_RECENT_CARD_W = 120
_RECENT_CARD_H = 180
_MAX_RECENT = 8


class RecentPlayedRow(QWidget):
    game_clicked = Signal(object)

    def __init__(
        self,
        store: PlaytimeStore,
        card_w: int = _RECENT_CARD_W,
        card_h: int = _RECENT_CARD_H,
        parent=None,
    ):
        super().__init__(parent)
        self._store = store
        self._games: list[Game] = []
        self._recent: list[Game] = []
        self._card_w, self._card_h = card_w, card_h
        self._items: list[dict] = []
        self._search_text = ""

        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        title = QLabel("RECENTLY PLAYED")
        title.setStyleSheet(
            f"color: {C.BLUE}; font-size: 11px; font-weight: 800;"
            f"letter-spacing: 1px; background: transparent;"
        )
        v.addWidget(title)

        self._empty = QLabel("Games you play will show up here.")
        self._empty.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 13px; background: transparent; padding: 18px 0;"
        )
        self._empty.setVisible(False)
        v.addWidget(self._empty)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        self._host = QWidget()
        self._host.setStyleSheet("background: transparent;")
        self._row = QHBoxLayout(self._host)
        self._row.setContentsMargins(8, 0, 8, 0)
        self._row.setSpacing(12)
        self._row.addStretch(1)
        self._scroll.setWidget(self._host)
        v.addWidget(self._scroll)

    # -- public API -----------------------------------------------------

    def set_games(self, games: list[Game]):
        self._games = games
        self._recent = self._recent_games()
        self._rebuild()

    def refresh(self):
        self._recent = self._recent_games()
        self._rebuild()

    def set_search(self, text: str):
        self._search_text = text
        self.setVisible(not text.strip())
        self.refresh()

    def set_card_art(self, game: Game, pix):
        for item in self._items:
            if item["game"] == game:
                item["card"].set_art(pix)
                return

    def cards(self) -> list[GameCard]:
        return [item["card"] for item in self._items]

    # -- internals ------------------------------------------------------

    def _recent_games(self) -> list[Game]:
        ranked = [
            g for g in self._games
            if self._store.last_played(game_key(g)) > 0
        ]
        ranked.sort(key=lambda g: self._store.last_played(game_key(g)), reverse=True)
        return ranked[:_MAX_RECENT]

    def _rebuild(self):
        for item in self._items:
            item["frame"].setParent(None)
            item["frame"].deleteLater()
        self._items.clear()

        for game in self._recent:
            self._items.append(self._build_item(game))

        self._empty.setVisible(not self._items)
        self._scroll.setVisible(bool(self._items))

    def _build_item(self, game: Game) -> dict:
        frame = QWidget()
        frame.setStyleSheet("background: transparent;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        card = GameCard(
            game, card_w=self._card_w, card_h=self._card_h, fit_art=True
        )
        card.clicked.connect(self.game_clicked)
        v.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)

        name = self._elide(game.name.replace("/", " / "))
        name_label = QLabel(name)
        name_label.setFixedWidth(self._card_w)
        name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        name_label.setStyleSheet(f"color: {C.TEXT}; font-size: 12px; background: transparent;")
        name_label.setToolTip(game.name)
        v.addWidget(name_label)

        time_label = QLabel(format_playtime(self._store.playtime(game_key(game))))
        time_label.setFixedWidth(self._card_w)
        time_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        time_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        v.addWidget(time_label)

        card.set_art(art.load_grid(game, allow_network=False))
        self._row.insertWidget(self._row.count() - 1, frame)
        return {"frame": frame, "card": card, "game": game}

    def _elide(self, text: str) -> str:
        font = QFont("Roboto", 12)
        fm = QFontMetrics(font)
        return fm.elidedText(text, Qt.TextElideMode.ElideRight, self._card_w)
