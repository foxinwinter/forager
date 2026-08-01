"""The Settings → Account tab: Steam sign-in + SteamGridDB token."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFormLayout, QInputDialog,
)

from forager.ui.theme import C
from forager.ui.settings_tabs import SettingsTab, _INPUT_QSS, _CHECK_QSS, _NOTE_QSS
from forager.ui.steam_login_worker import SteamLoginWorker
from forager.ui.steam_qr_dialog import SteamQrDialog

_PRIMARY_BTN_QSS = f"""
QPushButton {{ background-color: {C.ACCENT_1}; color: {C.BG}; border: none;
border-radius: {C.RADIUS}px; padding: 6px 16px; font-weight: 600; }}
QPushButton:hover {{ background-color: {C.ACCENT_2}; }}
QPushButton:disabled {{ background-color: {C.COLOR_2}; color: {C.TEXT_DIM}; }}
"""

_SECONDARY_BTN_QSS = f"""
QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};
 border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}
QPushButton:hover {{ background-color: {C.COLOR_3}; }}
"""


class AccountTab(SettingsTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        from forager.library import steam, steamgriddb

        self.setStyleSheet(f"background-color: {C.BG};")
        lay = QVBoxLayout(self)

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

        self._steam_signin_btn = QPushButton("Sign in with password")
        self._steam_signin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_signin_btn.setStyleSheet(_SECONDARY_BTN_QSS)
        self._steam_signin_btn.clicked.connect(self._on_steam_signin)
        self._steam_qr_btn = QPushButton("Sign in with QR")
        self._steam_qr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_qr_btn.setStyleSheet(_PRIMARY_BTN_QSS)
        self._steam_qr_btn.clicked.connect(self._on_steam_qr)
        self._steam_signout_btn = QPushButton("Sign out")
        self._steam_signout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_signout_btn.setStyleSheet(_SECONDARY_BTN_QSS)
        self._steam_signout_btn.clicked.connect(self._on_steam_signout)
        actions_layout.addWidget(self._steam_qr_btn)
        actions_layout.addWidget(self._steam_signin_btn)
        actions_layout.addWidget(self._steam_signout_btn)
        actions_layout.addStretch(1)
        lay.addWidget(actions)

        self._steam_status = QLabel()
        self._steam_status.setWordWrap(True)
        self._steam_status.setStyleSheet(_NOTE_QSS)
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
        self._token_save_btn.setStyleSheet(_SECONDARY_BTN_QSS)
        self._token_save_btn.clicked.connect(self._save_token)
        token_layout.addWidget(self._token_save_btn)
        token_layout.addStretch(1)
        lay.addWidget(token_row)

        self._token_status = QLabel()
        self._token_status.setWordWrap(True)
        self._token_status.setStyleSheet(_NOTE_QSS)
        lay.addWidget(self._token_status)
        self._update_token_status()

        note = QLabel(
            "Sign in with the Steam mobile app (QR code), or use username/password — "
            "the password flow is how you sign in without a phone (Steam Guard codes "
            "are asked for here when needed). Credentials and sessions live in your "
            "system keyring / DepotDownloader's account store, never in plaintext. "
            "Proton updates still use anonymous access."
        )
        note.setWordWrap(True)
        note.setStyleSheet(_NOTE_QSS)
        lay.addWidget(note)
        lay.addStretch(1)

    # -- steam sign-in --------------------------------------------------

    def _update_steam_status(self):
        from forager.library import steam

        user = steam.get_username()
        if user:
            method = steam.get_login_method()
            if method == "qr":
                self._steam_status.setText(
                    f"Signed in as {user} (QR session — game downloads are hands-free)."
                )
            else:
                self._steam_status.setText(f"Credentials stored for {user}.")
        else:
            self._steam_status.setText("Not signed in.")

    def _on_steam_qr(self):
        dlg = getattr(self, "_qr_dialog", None)
        if dlg is not None and dlg.isVisible():
            return
        dlg = SteamQrDialog(self.window())
        self._qr_dialog = dlg
        dlg.finished.connect(lambda _r: self._update_steam_status())
        dlg.open()

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
        steam.clear_session()
        self._steam_pass_edit.clear()
        self._update_steam_status()

    # -- SteamGridDB token ---------------------------------------------

    def _update_token_status(self):
        from forager.library import steamgriddb

        if steamgriddb.get_api_key():
            self._token_status.setText("API token set (used for cover art).")
        else:
            self._token_status.setText("No API token. Cover art falls back to Steam CDN/local files.")

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

    def save(self):
        self._save_token()

    def cancel_worker(self):
        dlg = getattr(self, "_qr_dialog", None)
        if dlg is not None:
            dlg.cancel()
        worker = getattr(self, "_steam_worker", None)
        if worker is not None and worker.isRunning():
            worker.cancel()
            worker.wait(3000)
