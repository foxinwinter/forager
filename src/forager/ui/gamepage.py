from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame,
)

from forager.core.game import Game
from forager.services import art
from forager.ui.banner import Banner
from forager.ui.theme import C
from forager.ui.icons import load_icon as load_bundled_icon


class GamePage(QWidget):
    play = Signal(object)
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Game | None = None
        self._logo: QPixmap | None = None

        self.setStyleSheet(f"background-color: {C.COLOR_1};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C.COLOR_1}; border: none; }}")

        content = QWidget()
        content.setStyleSheet(f"background: {C.COLOR_1};")
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 0, 16)
        v.setSpacing(16)

        self._banner = Banner()
        v.addWidget(self._banner)

        self._title = QLabel("")
        self._title.setFont(QFont("Roboto", 26, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        self._title.setWordWrap(True)
        v.addWidget(self._title)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self._play_btn = QPushButton()
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.setFixedHeight(48)
        self._play_btn.setMinimumWidth(220)
        self._play_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {C.GREEN}; border: none;
                border-radius: {C.RADIUS}px;
            }}
            QPushButton:hover {{ background-color: {C.GREEN_HOVER}; }}
            QPushButton:disabled {{ background-color: {C.COLOR_3}; }}
            """
        )
        play_lay = QHBoxLayout(self._play_btn)
        play_lay.setContentsMargins(20, 0, 16, 0)
        play_lay.setSpacing(5)
        play_icon = QLabel()
        play_icon.setPixmap(load_bundled_icon("play", "#ffffff").pixmap(20, 20))
        play_icon.setStyleSheet("background: transparent;")
        play_lay.addWidget(play_icon)
        play_text = QLabel("Play")
        play_text.setStyleSheet(
            f"background: transparent; color: #ffffff;"
            f"font-size: 17px; font-weight: 600;"
        )
        play_lay.addWidget(play_text)
        play_lay.addStretch(1)
        self._play_btn.clicked.connect(self._on_play)
        info_row.addWidget(self._play_btn)

        self._source_badge = QLabel("")
        self._source_badge.setStyleSheet(
            f"background-color: {C.COLOR_3}; color: {C.TEXT_DIM};"
            f"border-radius: {C.RADIUS}px; padding: 6px 12px; font-size: 12px;"
        )
        info_row.addWidget(self._source_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._path_label = QLabel("")
        self._path_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 12px; background: transparent;")
        self._path_label.setWordWrap(True)
        info_row.addWidget(self._path_label, stretch=1)

        v.addLayout(info_row)

        self._info_box = self._build_info_box()
        v.addWidget(self._info_box, alignment=Qt.AlignmentFlag.AlignLeft)

        v.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._banner.set_overlay(self._build_banner_overlay())
        self._banner_overlay = self._banner._overlay

    def _build_banner_overlay(self) -> QWidget:
        overlay = QWidget(self._banner)
        overlay.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(overlay)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(12)

        top = QHBoxLayout()
        back_btn = QPushButton("‹  Library")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(17, 17, 17, 170); color: {C.TEXT};
                border: none; border-radius: {C.RADIUS}px; padding: 8px 14px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: rgba(17, 17, 17, 230); }}
            """
        )
        back_btn.clicked.connect(self.back_requested)
        top.addWidget(back_btn)
        top.addStretch(1)
        lay.addLayout(top)

        lay.addStretch(1)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        self._logo_label.setMaximumWidth(520)
        self._logo_label.setMinimumHeight(90)
        lay.addWidget(self._logo_label)

        return overlay

    def _build_info_box(self) -> QFrame:
        box = QFrame()
        box.setFixedWidth(300)
        box.setStyleSheet(
            f"QFrame {{ background-color: {C.COLOR_2}; border: none;"
            f"border-radius: {C.RADIUS}px; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        header = QLabel("GAME INFO")
        header.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        v.addWidget(header)

        self._info_rows: dict[str, QLabel] = {}
        for key, label in (("Source", "source"), ("Location", "path"), ("App ID", "app_id")):
            row = QHBoxLayout()
            row.setSpacing(8)
            k = QLabel(key.upper())
            k.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px;")
            k.setFixedWidth(70)
            val = QLabel("")
            val.setStyleSheet(f"color: {C.TEXT}; font-size: 12px; background: transparent;")
            val.setWordWrap(True)
            row.addWidget(k)
            row.addWidget(val, stretch=1)
            v.addLayout(row)
            self._info_rows[label] = val

        v.addStretch(1)
        return box

    def _on_play(self):
        if self.game is not None:
            self.play.emit(self.game)

    def set_game(self, game: Game):
        self.game = game

        hero = art.load_hero(game, allow_network=False)
        if hero is None:
            hero = art.placeholder_card(game, 900, 420)
        self._banner.set_source(hero)

        self._logo = art.load_logo(game)
        if self._logo is not None:
            self._logo_label.setPixmap(
                self._logo.scaledToWidth(
                    min(520, self._logo.width()),
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._title.setText("")
        else:
            self._logo_label.clear()
            self._title.setText(game.name.replace("/", " / "))

        self._source_badge.setText(game.source_name)
        self._path_label.setText(game.display_path)
        self._info_rows["source"].setText(game.source_name)
        self._info_rows["path"].setText(game.display_path)
        self._info_rows["app_id"].setText(game.app_id or "—")

    def set_hero(self, pix: QPixmap | None):
        if pix is None:
            return
        self._banner.set_source(pix)
