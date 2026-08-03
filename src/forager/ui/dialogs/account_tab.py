"""The Settings → Account tab: Steam sign-in + SteamGridDB token."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton,
)

from forager.ui.theme import C
from forager.ui.dialogs.settings_tabs import SettingsTab, _INPUT_QSS, _NOTE_QSS
from forager.ui.dialogs.steam_auth_dialog import SteamAuthDialog
from forager.ui.dialogs.steamgriddb_dialog import SteamGridDBTokenDialog

_PRIMARY_BTN_QSS = f"""
QPushButton {{ background-color: {C.ACCENT_1}; color: {C.TEXT}; border: none;
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
        from forager.steam import account, sgdb

        self._account = account
        self._sgdb = sgdb

        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        card, card_lay = self._section("Steam account")
        self._steam_status = QLabel()
        self._steam_status.setWordWrap(True)
        self._steam_status.setStyleSheet(_NOTE_QSS)
        card_lay.addWidget(self._steam_status)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._steam_web_btn = QPushButton("Sign in with Steam")
        self._steam_web_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_web_btn.setStyleSheet(_PRIMARY_BTN_QSS)
        self._steam_web_btn.clicked.connect(self._on_steam_signin)
        self._steam_signout_btn = QPushButton("Sign out")
        self._steam_signout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._steam_signout_btn.setStyleSheet(_SECONDARY_BTN_QSS)
        self._steam_signout_btn.clicked.connect(self._on_steam_signout)
        actions.addWidget(self._steam_web_btn)
        actions.addWidget(self._steam_signout_btn)
        actions.addStretch(1)
        card_lay.addLayout(actions)
        lay.addWidget(card)

        card, card_lay = self._section("SteamGridDB")
        token_row = QHBoxLayout()
        token_row.setSpacing(8)
        self._token_edit = QLineEdit(self._sgdb.get_api_key() or "")
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setStyleSheet(_INPUT_QSS)
        self._token_edit.setPlaceholderText("No API token set")
        token_row.addWidget(self._token_edit, stretch=1)
        self._token_save_btn = QPushButton("Save token")
        self._token_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._token_save_btn.setStyleSheet(_SECONDARY_BTN_QSS)
        self._token_save_btn.clicked.connect(self._save_token)
        token_row.addWidget(self._token_save_btn)
        card_lay.addLayout(token_row)

        self._token_get_btn = QPushButton("Get token")
        self._token_get_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._token_get_btn.setStyleSheet(_PRIMARY_BTN_QSS)
        self._token_get_btn.clicked.connect(self._on_get_token)
        card_lay.addWidget(self._token_get_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._token_status = QLabel()
        self._token_status.setWordWrap(True)
        self._token_status.setStyleSheet(_NOTE_QSS)
        card_lay.addWidget(self._token_status)
        lay.addWidget(card)

        self._note(
            lay,
            "Sign in with the Steam mobile app (QR code) or your password plus "
            "Steam Guard code — all handled right here, no browser needed. Your "
            "session is stored in the system keyring, never in plaintext. Proton "
            "updates still use anonymous access.",
        )
        lay.addStretch(1)

        self._update_steam_status()
        self._update_token_status()

    # -- steam sign-in --------------------------------------------------

    def _update_steam_status(self):
        user = self._account.get_username()
        if user:
            method = self._account.get_login_method()
            if method in ("web", "qr"):
                self._steam_status.setText(
                    f"Signed in as {user} (Steam session)."
                )
            elif method == "password":
                self._steam_status.setText(
                    f"Credentials stored for {user} — hands-free DepotDownloader session."
                )
            else:
                self._steam_status.setText(f"Credentials stored for {user}.")
        else:
            self._steam_status.setText("Not signed in.")

    def _on_steam_signin(self):
        dlg = getattr(self, "_web_dialog", None)
        if dlg is not None and dlg.isVisible():
            return
        dlg = SteamAuthDialog(self.window())
        self._web_dialog = dlg
        dlg.finished.connect(lambda _r: self._update_steam_status())
        dlg.open()

    def _on_steam_signout(self):
        self._account.clear_credentials()
        self._account.clear_session()
        self._update_steam_status()

    # -- SteamGridDB token ---------------------------------------------

    def _update_token_status(self):
        if self._sgdb.get_api_key():
            self._token_status.setText("API token set (used for cover art).")
        else:
            self._token_status.setText("No API token. Cover art falls back to Steam CDN/local files.")

    def _on_get_token(self):
        dlg = getattr(self, "_sgdb_dialog", None)
        if dlg is not None and dlg.isVisible():
            return
        dlg = SteamGridDBTokenDialog(self.window())
        self._sgdb_dialog = dlg
        dlg.finished.connect(lambda _r: self._update_token_status())
        dlg.open()

    def _save_token(self, silent: bool = False):
        token = self._token_edit.text().strip()
        try:
            if token:
                self._sgdb.set_api_key(token)
                self._token_status.setText("API token saved.")
            else:
                self._sgdb.set_api_key("")
                self._token_status.setText("API token cleared.")
        except Exception as e:
            self._token_status.setText(f"Could not save token: {e}")

    def save(self):
        self._save_token()

    def cancel_worker(self):
        dlg = getattr(self, "_web_dialog", None)
        if dlg is not None:
            dlg.cancel()
        sgdb = getattr(self, "_sgdb_dialog", None)
        if sgdb is not None:
            sgdb.cancel()
