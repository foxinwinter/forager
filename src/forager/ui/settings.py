from __future__ import annotations
import queue
import threading
from PySide6.QtCore import Qt, QSize, Signal, QThread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QCheckBox, QStackedWidget, QButtonGroup, QFileDialog,
    QDialogButtonBox, QFormLayout, QGroupBox, QRadioButton, QInputDialog,
)

from forager.core.config import settings
from forager.library import proton
from forager.ui.theme import C
from forager.ui.icons import load_icon as load_bundled_icon

DISPLAY_SIZES = [
    ("small", "Small", 120, 180),
    ("medium", "Medium", 165, 248),
    ("large", "Large", 250, 375),
]


def resolve_card_size(key: str) -> tuple[int, int]:
    for k, _label, w, h in DISPLAY_SIZES:
        if k == key:
            return (w, h)
    return (165, 248)


class SteamLoginWorker(QThread):
    guard_requested = Signal(str)
    done = Signal(bool, str)

    def __init__(self, username: str, password: str, remember: bool, parent=None):
        super().__init__(parent)
        self._username = username
        self._password = password
        self._remember = remember
        self._codes: queue.Queue = queue.Queue()
        self._cancel = threading.Event()

    def run(self):
        from forager.library import steam

        def guard_prompt(message: str):
            self.guard_requested.emit(message)
            return self._codes.get()

        try:
            ok, detail = steam.verify_login(
                self._username, self._password, self._remember,
                guard_prompt, cancel_event=self._cancel,
            )
        except Exception as e:
            ok, detail = False, str(e)
        self.done.emit(ok, detail)

    def answer_guard(self, code: str | None):
        self._codes.put(code)

    def cancel(self):
        self._cancel.set()
        self._codes.put(None)


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
        body = QHBoxLayout()
        body.setSpacing(12)

        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        body.addLayout(self._build_nav(nav_group))

        self._pages = QStackedWidget()
        self._pages.addWidget(self._build_library_tab())
        self._pages.addWidget(self._build_proton_tab())
        self._pages.addWidget(self._build_account_tab())
        body.addWidget(self._pages, stretch=1)

        nav_group.buttonClicked.connect(
            lambda btn: self._pages.setCurrentIndex(self._page_order.index(btn.text()))
        )
        v.addLayout(body)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};"
            f" border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
            f"QPushButton:default {{ background-color: {C.ACCENT_1}; color: {C.BG}; border: none; }}"
        )
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
            btn.setStyleSheet(
                f"""
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
            )
            group.addButton(btn)
            nav.addWidget(btn)
            first = False
        nav.addStretch(1)
        return nav

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
        note.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(note)
        lay.addStretch(1)
        return tab

    def _build_proton_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(tab)

        form = QFormLayout()
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

    def _build_account_tab(self) -> QWidget:
        from forager.library import steam, steamgriddb

        tab = QWidget()
        tab.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(tab)

        steam_box = self._group("Steam account")
        steam_form = QFormLayout()
        self._steam_user_edit = QLineEdit(steam.get_username() or "")
        self._steam_user_edit.setStyleSheet(_INPUT_QSS)
        self._steam_pass_edit = QLineEdit(steam.get_password() or "")
        self._steam_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._steam_pass_edit.setStyleSheet(_INPUT_QSS)
        steam_form.addRow("Username", self._steam_user_edit)
        steam_form.addRow("Password", self._steam_pass_edit)

        self._steam_remember = QCheckBox("Keep me signed in (store refresh token)")
        self._steam_remember.setChecked(True)
        self._steam_remember.setStyleSheet(_CHECK_QSS)
        steam_form.addRow("", self._steam_remember)
        steam_box.setLayout(steam_form)
        lay.addWidget(steam_box)

        actions = QWidget()
        actions.setStyleSheet("background: transparent;")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        self._steam_signin_btn = QPushButton("Sign in")
        self._steam_signin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_signin_btn.setStyleSheet(
            f"QPushButton {{ background-color: {C.ACCENT_1}; color: {C.BG}; border: none;"
            f"border-radius: {C.RADIUS}px; padding: 6px 16px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {C.ACCENT_2}; }}"
            f"QPushButton:disabled {{ background-color: {C.COLOR_2}; color: {C.TEXT_DIM}; }}"
        )
        self._steam_signin_btn.clicked.connect(self._on_steam_signin)
        self._steam_signout_btn = QPushButton("Sign out")
        self._steam_signout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_signout_btn.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};"
            f" border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
        )
        self._steam_signout_btn.clicked.connect(self._on_steam_signout)
        actions_layout.addWidget(self._steam_signin_btn)
        actions_layout.addWidget(self._steam_signout_btn)
        actions_layout.addStretch(1)
        lay.addWidget(actions)

        self._steam_status = QLabel()
        self._steam_status.setWordWrap(True)
        self._steam_status.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(self._steam_status)

        self._update_steam_status()

        sdb_box = self._group("SteamGridDB")
        sdb_form = QFormLayout()
        self._token_edit = QLineEdit(steamgriddb.get_api_key() or "")
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setStyleSheet(_INPUT_QSS)
        self._token_edit.setPlaceholderText("No API token set")
        sdb_form.addRow("API token", self._token_edit)
        sdb_box.setLayout(sdb_form)
        lay.addWidget(sdb_box)

        token_row = QWidget()
        token_row.setStyleSheet("background: transparent;")
        token_layout = QHBoxLayout(token_row)
        token_layout.setContentsMargins(0, 0, 0, 0)
        token_layout.setSpacing(8)
        self._token_save_btn = QPushButton("Save token")
        self._token_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._token_save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};"
            f" border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_3}; }}"
        )
        self._token_save_btn.clicked.connect(self._save_token)
        token_layout.addWidget(self._token_save_btn)
        token_layout.addStretch(1)
        lay.addWidget(token_row)

        self._token_status = QLabel()
        self._token_status.setWordWrap(True)
        self._token_status.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(self._token_status)
        self._update_token_status()

        note = QLabel(
            "Steam credentials are kept in your system keyring (never stored in plaintext). "
            "Signing in validates them with DepotDownloader; Steam Guard codes are asked for here "
            "when needed. Proton updates still use anonymous access."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;")
        lay.addWidget(note)
        lay.addStretch(1)
        return tab

    def _update_steam_status(self):
        from forager.library import steam

        user = steam.get_username()
        if user:
            self._steam_status.setText(f"Credentials stored for {user}.")
        else:
            self._steam_status.setText("Not signed in.")

    def _update_token_status(self):
        from forager.library import steamgriddb

        if steamgriddb.get_api_key():
            self._token_status.setText("API token set (used for cover art).")
        else:
            self._token_status.setText("No API token. Cover art falls back to Steam CDN/local files.")

    def _on_steam_signin(self):
        from forager.library import steam

        user = self._steam_user_edit.text().strip()
        password = self._steam_pass_edit.text()
        if not user or not password:
            self._steam_status.setText("Enter your Steam username and password first.")
            return
        worker = getattr(self, "_steam_worker", None)
        if worker is not None and worker.isRunning():
            return
        self._steam_login_user = user
        self._steam_login_password = password
        self._steam_status.setText(f"Signing in as {user}…")
        self._steam_signin_btn.setEnabled(False)
        self._steam_worker = SteamLoginWorker(user, password, self._steam_remember.isChecked(), self)
        self._steam_worker.guard_requested.connect(self._on_guard_requested)
        self._steam_worker.done.connect(self._on_steam_login_done)
        self._steam_worker.start()

    def _on_guard_requested(self, message: str):
        code, ok = QInputDialog.getText(self, "Steam Guard", message)
        worker = getattr(self, "_steam_worker", None)
        if worker is not None:
            worker.answer_guard(code if ok else None)

    def _on_steam_login_done(self, ok: bool, detail: str):
        from forager.library import steam

        self._steam_signin_btn.setEnabled(True)
        if ok:
            try:
                steam.set_credentials(self._steam_login_user, self._steam_login_password)
            except Exception as e:
                self._steam_status.setText(f"Signed in, but could not store credentials: {e}")
                return
            self._steam_status.setText(detail or "Signed in.")
        else:
            self._steam_status.setText(detail or "Sign-in failed.")

    def _on_steam_signout(self):
        from forager.library import steam

        steam.clear_credentials()
        self._steam_pass_edit.clear()
        self._update_steam_status()

    def _save_token(self, silent: bool = False):
        from forager.library import steamgriddb

        token = self._token_edit.text().strip()
        try:
            if token:
                steamgriddb.set_api_key(token)
                self._token_status.setText("API token saved.")
            else:
                steamgriddb.set_api_key("")
                self._token_status.setText("API token cleared.")
        except Exception as e:
            self._token_status.setText(f"Could not save token: {e}")

    def done(self, result):
        worker = getattr(self, "_steam_worker", None)
        if worker is not None and worker.isRunning():
            worker.cancel()
            worker.wait(3000)
        super().done(result)

    def _save(self):
        settings.set("games_dir", self._games_dir_edit.text().strip() or str(settings.games_dir))
        settings.set("steam_appcache", self._steam_cache_edit.text().strip() or str(settings.steam_appcache))
        selected = next((k for k, rb in self._size_radios.items() if rb.isChecked()), "medium")
        settings.set("display_size", selected)
        settings.data.setdefault("proton", {})["prefix_name"] = self._prefix_edit.text().strip() or "single"
        features = settings.data.setdefault("proton", {}).setdefault("features", {})
        for name, cb in self._features.items():
            features[name] = cb.isChecked()
        settings.save()
        self._save_token()
        self.accept()
