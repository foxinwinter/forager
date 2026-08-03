"""The Library and Proton settings tabs, plus shared tab helpers.

Sections follow SpaceTheme's settings look: a blue weight-800 title over a
``color-3`` card whose rows are ``color-2`` cards. The display-size picker
mirrors Steam's radiogroup (selected row fills with the accent colour).
"""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QRadioButton, QToolButton,
    QFrame, QFileDialog,
)

from forager.core.config import settings
from forager.compatibility import proton
from forager.ui.icons import load_icon
from forager.ui.theme import C

DISPLAY_SIZES = [
    ("small", "Small", 120, 180),
    ("medium", "Medium", 165, 248),
    ("large", "Large", 250, 375),
]

_INPUT_QSS = f"""
QLineEdit {{
    background-color: {C.COLOR_3}; color: {C.TEXT};
    border: none; border-radius: {C.RADIUS}px;
    padding: 6px 10px;
}}
QLineEdit:focus {{ border: 1px solid {C.ACCENT_1}; }}
"""

_NOTE_QSS = f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;"

_SECTION_TITLE_QSS = f"color: {C.BLUE}; font-size: 13px; font-weight: 800; background: transparent;"

_SECTION_QSS = f"""
QFrame#Section {{
    background-color: {C.COLOR_3};
    border: none;
    border-radius: {C.RADIUS}px;
}}
"""

_ROW_QSS = f"""
QFrame#Row {{
    background-color: {C.COLOR_2};
    border: none;
    border-radius: 6px;
}}
"""

_ROW_LABEL_QSS = f"color: {C.TEXT}; font-size: 13px; font-weight: 500; background: transparent;"

_SECONDARY_BTN_QSS = f"""
QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};
 border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px;
 padding: 5px 14px; font-size: 13px; font-weight: 500; }}
QPushButton:hover {{ background-color: {C.COLOR_3}; }}
"""

_PRIMARY_BTN_QSS = f"""
QPushButton {{ background-color: {C.ACCENT_1}; color: {C.TEXT}; border: none;
 border-radius: {C.RADIUS}px; padding: 5px 16px; font-size: 13px; font-weight: 600; }}
QPushButton:hover {{ background-color: {C.ACCENT_2}; }}
QPushButton:disabled {{ background-color: {C.COLOR_2}; color: {C.TEXT_DIM}; }}
"""

_CHECK_QSS = f"""
QCheckBox {{ color: {C.TEXT}; background: transparent; spacing: 10px; font-size: 13px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 2px solid {C.COLOR_5}; border-radius: 4px;
    background-color: {C.COLOR_3};
}}
QCheckBox::indicator:hover {{ border: 3px solid {C.COLOR_5}; }}
QCheckBox::indicator:checked {{
    background-color: {C.ACCENT_1};
    border: 2px solid {C.ACCENT_1};
    image: none;
}}
"""

_RADIO_QSS = f"""
QRadioButton {{
    background-color: {C.COLOR_2}; color: {C.TEXT};
    border: none; border-radius: 6px;
    padding: 8px 12px; font-size: 13px;
    spacing: 10px;
}}
QRadioButton:hover {{ background-color: {C.COLOR_4}; }}
QRadioButton:checked {{
    background-color: {C.ACCENT_1}; color: {C.TEXT};
    font-weight: 600;
}}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 2px solid {C.COLOR_5}; border-radius: 8px;
    background-color: {C.COLOR_3};
}}
QRadioButton::indicator:hover {{ border: 3px solid {C.COLOR_5}; }}
QRadioButton::indicator:checked {{
    border: 2px solid {C.TEXT}; background-color: {C.TEXT};
}}
"""


class CollapsibleSection(QWidget):
    """A titled section whose body folds away when the header is clicked."""

    def __init__(self, title: str, parent=None, collapsed: bool = True):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self._header = QToolButton()
        self._header.setText(title)
        self._header.setCheckable(True)
        self._header.setChecked(not collapsed)
        self._header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._header.setArrowType(
            Qt.ArrowType.RightArrow if collapsed else Qt.ArrowType.DownArrow
        )
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(
            f"QToolButton {{ background: transparent; color: {C.TEXT_DIM};"
            f" border: none; font-size: 13px; font-weight: 600; padding: 4px 2px;"
            f" text-align: left; }}"
            f"QToolButton:hover {{ color: {C.TEXT}; }}"
        )
        self._header.toggled.connect(self._toggle)
        v.addWidget(self._header)

        self._frame = QFrame()
        self._frame.setStyleSheet(
            f"QFrame {{ background: {C.COLOR_2}; border: 1px solid {C.COLOR_3};"
            f" border-radius: {C.RADIUS}px; }}"
        )
        self._body = QVBoxLayout(self._frame)
        self._body.setContentsMargins(10, 10, 10, 10)
        self._body.setSpacing(8)
        v.addWidget(self._frame)
        self._frame.setVisible(not collapsed)

    def _toggle(self, checked: bool):
        self._header.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        self._frame.setVisible(checked)
        if self.parentWidget() is not None:
            self.parentWidget().updateGeometry()

    def body_layout(self) -> QVBoxLayout:
        return self._body


class SettingsTab(QWidget):
    """Shared helpers for building a settings page."""

    def _section(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        """A SpaceTheme-style section: blue title over a color-3 card.

        Returns the outer widget (add it to the page) and the card's layout.
        """
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        label = QLabel(title)
        label.setStyleSheet(_SECTION_TITLE_QSS)
        col.addWidget(label)

        card = QFrame()
        card.setObjectName("Section")
        card.setStyleSheet(_SECTION_QSS)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        col.addWidget(card)
        return box, card_layout

    def _row(self, layout: QVBoxLayout, title: str | None = None) -> QVBoxLayout:
        row = QFrame()
        row.setObjectName("Row")
        row.setStyleSheet(_ROW_QSS)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(6)
        if title:
            label = QLabel(title)
            label.setStyleSheet(_ROW_LABEL_QSS)
            row_layout.addWidget(label)
        layout.addWidget(row)
        return row_layout

    def _path_row(self, form: QVBoxLayout, title: str, value: str) -> QLineEdit:
        row = self._row(form, title)
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        edit = QLineEdit(value)
        edit.setStyleSheet(_INPUT_QSS)
        btn = QPushButton("Browse…")
        btn.setStyleSheet(_SECONDARY_BTN_QSS)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._browse(edit))
        lay.addWidget(edit, stretch=1)
        lay.addWidget(btn)
        row.addLayout(lay)
        return edit

    def _browse(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Choose folder", edit.text() or str(settings.games_dir))
        if path:
            edit.setText(path)

    def _note(self, layout: QVBoxLayout, text: str) -> QLabel:
        note = QLabel(text)
        note.setWordWrap(True)
        note.setStyleSheet(_NOTE_QSS)
        layout.addWidget(note)
        return note


class LibraryTab(SettingsTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        card, card_lay = self._section("Directories")
        self._games_dir_edit = self._path_row(card_lay, "Game library folder", str(settings.games_dir))
        self._steam_cache_edit = self._path_row(card_lay, "Steam appcache/librarycache", str(settings.steam_appcache))
        lay.addWidget(card)

        card, card_lay = self._section("Display size")
        current = settings.get("display_size", "medium")
        self._size_radios: dict[str, QRadioButton] = {}
        for key, label, w, h in DISPLAY_SIZES:
            rb = QRadioButton(f"{label}  ({w}×{h})")
            rb.setChecked(key == current)
            rb.setStyleSheet(_RADIO_QSS)
            self._size_radios[key] = rb
            card_lay.addWidget(rb)
        card_lay.addStretch(1)
        lay.addWidget(card)

        self._note(
            lay,
            "The Steam folder is used for already-downloaded cover art and to "
            "locate your Steam client install.",
        )
        lay.addStretch(1)

    def games_dir_text(self) -> str:
        return self._games_dir_edit.text()

    def steam_cache_text(self) -> str:
        return self._steam_cache_edit.text()

    def selected_card_size(self) -> str:
        return next((k for k, rb in self._size_radios.items() if rb.isChecked()), "medium")


class ProtonTab(SettingsTab):
    update_proton_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        card, card_lay = self._section("Prefix")
        row = self._row(card_lay, "Proton prefix")
        status = QLabel(self._proton_status())
        status.setWordWrap(True)
        status.setStyleSheet(_NOTE_QSS)
        row.addWidget(status)
        lay.addWidget(card)

        card, card_lay = self._section("Add to prefix")
        self._features: dict[str, QCheckBox] = {}
        for name, (label, desc) in proton.FEATURES.items():
            cb = QCheckBox(f"{label}  —  {desc}")
            cb.setChecked(settings.proton_feature(name))
            cb.setStyleSheet(_CHECK_QSS)
            self._features[name] = cb
            card_lay.addWidget(cb)
        card_lay.addStretch(1)
        lay.addWidget(card)

        update = QPushButton("Update Proton…")
        update.setIcon(load_icon("download", C.TEXT))
        update.setCursor(Qt.CursorShape.PointingHandCursor)
        update.setStyleSheet(_PRIMARY_BTN_QSS)
        update.clicked.connect(self.update_proton_requested)
        lay.addWidget(update)
        lay.addStretch(1)

    def _proton_status(self) -> str:
        version = proton.proton_version()
        prefix = proton.proton_prefix_dir()
        if version:
            return f"Proton {version}  ·  prefix: {prefix}"
        return f"Proton not installed  ·  prefix: {prefix}"

    def feature_values(self) -> dict[str, bool]:
        return {name: cb.isChecked() for name, cb in self._features.items()}
