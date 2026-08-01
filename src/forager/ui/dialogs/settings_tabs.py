"""The Library and Proton settings tabs, plus shared tab helpers."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFormLayout, QGroupBox, QRadioButton,
    QToolButton, QFrame, QFileDialog,
)

from forager.core.config import settings
from forager.library import proton
from forager.ui.theme import C

DISPLAY_SIZES = [
    ("small", "Small", 120, 180),
    ("medium", "Medium", 165, 248),
    ("large", "Large", 250, 375),
]

_INPUT_QSS = f"""
QLineEdit {{
    background-color: {C.COLOR_2}; color: {C.TEXT};
    border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px;
    padding: 5px 8px;
}}
QLineEdit:focus {{ border: 1px solid {C.ACCENT_1}; }}
"""

_CHECK_QSS = f"""
QCheckBox {{ color: {C.TEXT}; background: transparent; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {C.COLOR_3}; border-radius: 4px; background: {C.COLOR_2};
}}
QCheckBox::indicator:checked {{ background-color: {C.ACCENT_1}; }}
"""

_SECONDARY_BTN_QSS = f"""
QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};
 border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}
QPushButton:hover {{ background-color: {C.COLOR_3}; }}
"""

_NOTE_QSS = f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;"


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

    def _group(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setStyleSheet(
            f"QGroupBox {{ color: {C.TEXT_DIM}; border: 1px solid {C.COLOR_3};"
            f" border-radius: {C.RADIUS}px; margin-top: 12px; padding-top: 6px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
            f"QLabel {{ color: {C.TEXT}; background: transparent; }}"
        )
        return box

    def _path_row(self, form: QFormLayout, label: str, value: str) -> QLineEdit:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(value)
        edit.setStyleSheet(_INPUT_QSS)
        btn = QPushButton("Browse…")
        btn.setStyleSheet(_SECONDARY_BTN_QSS)
        btn.clicked.connect(lambda: self._browse(edit))
        lay.addWidget(edit, stretch=1)
        lay.addWidget(btn)
        form.addRow(QLabel(label), row)
        return edit

    def _browse(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Choose folder", edit.text() or str(settings.games_dir))
        if path:
            edit.setText(path)


class LibraryTab(SettingsTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(self)

        form = QFormLayout()
        self._games_dir_edit = self._path_row(form, "Game library folder", str(settings.games_dir))
        self._steam_cache_edit = self._path_row(form, "Steam appcache/librarycache", str(settings.steam_appcache))
        box = self._group("Directories")
        box.setLayout(form)
        lay.addWidget(box)

        size_box = self._group("Display size")
        size_lay = QVBoxLayout(size_box)
        current = settings.get("display_size", "medium")
        self._size_radios: dict[str, QRadioButton] = {}
        for key, label, w, h in DISPLAY_SIZES:
            rb = QRadioButton(f"{label}  ({w}×{h})")
            rb.setChecked(key == current)
            rb.setStyleSheet(
                f"QRadioButton {{ color: {C.TEXT}; background: transparent; spacing: 8px; }}"
                f"QRadioButton::indicator {{ width: 16px; height: 16px;"
                f" border: 1px solid {C.COLOR_3}; border-radius: 8px; background: {C.COLOR_2}; }}"
                f"QRadioButton::indicator:checked {{ background-color: {C.ACCENT_1}; }}"
            )
            self._size_radios[key] = rb
            size_lay.addWidget(rb)
        lay.addWidget(size_box)

        note = QLabel("Steam folder is used for already-downloaded cover art and to locate your Steam client install.")
        note.setWordWrap(True)
        note.setStyleSheet(_NOTE_QSS)
        lay.addWidget(note)
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
        self.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(self)

        form = QFormLayout()
        form.addRow("Proton", QLabel("Prefix lives inside the Proton folder"))
        box = self._group("Prefix")
        box.setLayout(form)
        lay.addWidget(box)

        feat_box = self._group("Add to prefix")
        feat_lay = QVBoxLayout(feat_box)
        self._features: dict[str, QCheckBox] = {}
        for name, (label, desc) in proton.FEATURES.items():
            cb = QCheckBox(f"{label}  —  {desc}")
            cb.setChecked(settings.proton_feature(name))
            cb.setStyleSheet(_CHECK_QSS)
            self._features[name] = cb
            feat_lay.addWidget(cb)
        lay.addWidget(feat_box)

        status = QLabel(self._proton_status())
        status.setWordWrap(True)
        status.setStyleSheet(_NOTE_QSS)
        lay.addWidget(status)

        update = QPushButton("Update Proton…")
        update.setStyleSheet(_SECONDARY_BTN_QSS)
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
