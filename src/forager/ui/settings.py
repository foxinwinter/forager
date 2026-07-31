from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QCheckBox, QTabWidget, QFileDialog, QDialogButtonBox,
    QFormLayout, QGroupBox,
)

from forager.core.config import settings
from forager.library import proton
from forager.ui.theme import C

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


class SettingsDialog(QDialog):
    update_proton_requested = Signal()
    games_dir_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(560, 420)
        self.setStyleSheet(f"background-color: {C.BG}; color: {C.TEXT};")

        self._features: dict[str, QCheckBox] = {}

        v = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_library_tab(), "Library")
        tabs.addTab(self._build_proton_tab(), "Proton")
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {C.COLOR_3}; }}"
            f"QTabBar::tab {{ background: {C.COLOR_2}; color: {C.TEXT_DIM}; padding: 8px 18px; border: none; }}"
            f"QTabBar::tab:selected {{ color: {C.TEXT}; border-bottom: 2px solid {C.ACCENT_1}; }}"
        )
        v.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};"
            f" border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
            f"QPushButton:default {{ background-color: {C.ACCENT_1}; color: {C.BG}; border: none; }}"
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _group(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setStyleSheet(
            f"QGroupBox {{ color: {C.TEXT_DIM}; border: 1px solid {C.COLOR_3};"
            f" border-radius: {C.RADIUS}px; margin-top: 12px; padding-top: 6px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
        )
        return box

    def _path_row(self, form: QFormLayout, label: str, value: str) -> QLineEdit:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(value)
        edit.setStyleSheet(_INPUT_QSS)
        btn = QPushButton("Browse…")
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};"
            f" border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 5px 12px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
        )
        btn.clicked.connect(lambda: self._browse(edit))
        lay.addWidget(edit, stretch=1)
        lay.addWidget(btn)
        form.addRow(QLabel(label), row)
        return edit

    def _browse(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Choose folder", edit.text() or str(settings.games_dir))
        if path:
            edit.setText(path)

    def _build_library_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(tab)
        form = QFormLayout()
        form.setStyleSheet("QLabel { color: %s; background: transparent; }" % C.TEXT)
        self._games_dir_edit = self._path_row(form, "Game library folder", str(settings.games_dir))
        self._steam_cache_edit = self._path_row(form, "Steam appcache/librarycache", str(settings.steam_appcache))
        lay.addWidget(self._group("Directories"))
        box = self._group("Directories")
        box.setLayout(form)
        lay.addWidget(box)
        note = QLabel("Steam folder is used for already-downloaded cover art and to locate your Steam client install.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(note)
        lay.addStretch(1)
        return tab

    def _build_proton_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(tab)

        form = QFormLayout()
        form.setStyleSheet("QLabel { color: %s; background: transparent; }" % C.TEXT)
        self._prefix_edit = QLineEdit(settings.proton_prefix_name)
        self._prefix_edit.setStyleSheet(_INPUT_QSS)
        form.addRow("Shared prefix name", self._prefix_edit)
        box = self._group("Prefix")
        box.setLayout(form)
        lay.addWidget(box)

        feat_box = self._group("Add to prefix")
        feat_lay = QVBoxLayout(feat_box)
        for name, (label, desc) in proton.FEATURES.items():
            cb = QCheckBox(f"{label}  —  {desc}")
            cb.setChecked(settings.proton_feature(name))
            cb.setStyleSheet(_CHECK_QSS)
            self._features[name] = cb
            feat_lay.addWidget(cb)
        lay.addWidget(feat_box)

        status = QLabel(self._proton_status())
        status.setWordWrap(True)
        status.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(status)

        update = QPushButton("Update Proton…")
        update.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};"
            f" border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
        )
        update.clicked.connect(self._request_update)
        lay.addWidget(update)
        lay.addStretch(1)
        return tab

    def _proton_status(self) -> str:
        version = proton.proton_version()
        prefix = proton.proton_prefix_dir()
        if version:
            return f"Proton {version}  ·  prefix: {prefix}"
        return f"Proton not installed  ·  prefix: {prefix}"

    def _request_update(self):
        self.update_proton_requested.emit()

    def _save(self):
        settings.set("games_dir", self._games_dir_edit.text().strip() or str(settings.games_dir))
        settings.set("steam_appcache", self._steam_cache_edit.text().strip() or str(settings.steam_appcache))
        settings.data.setdefault("proton", {})["prefix_name"] = self._prefix_edit.text().strip() or "single"
        features = settings.data.setdefault("proton", {}).setdefault("features", {})
        for name, cb in self._features.items():
            features[name] = cb.isChecked()
        settings.save()
        self.accept()
