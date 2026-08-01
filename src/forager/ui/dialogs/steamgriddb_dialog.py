"""SteamGridDB API token: guided sign-in in an embedded webview.

Opens SteamGridDB's login page so the user can create an account or sign in
with their Steam account in one click, then jumps straight to the API-key page
once a session is detected. The key is never auto-copied: the page shows the
'Create API Key' button and the user pastes the key into the Settings →
Account → SteamGridDB field.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from forager.ui.theme import C

LOGIN_URL = "https://www.steamgriddb.com/login"
API_URL = "https://www.steamgriddb.com/profile/preferences/api"

_POLL_JS = """
window.__foragerSgdbLoggedIn = false;
fetch('/api/public/user', { method: 'GET', credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (d) {
        window.__foragerSgdbLoggedIn = !!(d && d.success === true);
    })
    .catch(function () { window.__foragerSgdbLoggedIn = false; });
"""

_READ_JS = "window.__foragerSgdbLoggedIn === true;"

_DIALOG_QSS = f"""
QDialog {{ background-color: {C.BG}; }}
QLabel#sgdbStatus {{ color: {C.TEXT_DIM}; font-size: 11px;
 background: {C.COLOR_2}; padding: 6px 12px; }}
"""


class SteamGridDBTokenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SteamGridDB API token")
        self.setModal(True)
        self.resize(900, 640)
        self.setMinimumSize(640, 480)
        self.setStyleSheet(_DIALOG_QSS)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._view = QWebEngineView(self)
        lay.addWidget(self._view, 1)

        self._status = QLabel(
            "Sign in with Steam to create or access your SteamGridDB account — "
            "it's free and takes one click. We'll jump to your API key page next."
        )
        self._status.setObjectName("sgdbStatus")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._navigated = False
        self._on_api_page = False

        self._view.loadFinished.connect(self._on_load_finished)
        self._view.load(QUrl(LOGIN_URL))

        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        self._poll()

    def _poll(self):
        self._view.page().runJavaScript(_POLL_JS)
        QTimer.singleShot(700, self._read_poll)

    def _read_poll(self):
        self._view.page().runJavaScript(_READ_JS, self._on_poll)

    def _on_poll(self, logged_in: bool):
        if logged_in and not self._navigated:
            self._navigated = True
            self._status.setText("Signed in! Opening your API key page…")
            self._view.setUrl(QUrl(API_URL))

    def _on_load_finished(self, ok: bool):
        if self._on_api_page:
            return
        if self._navigated and ok:
            self._on_api_page = True
            self._status.setText(
                "Click the 'Create API Key' button, copy the API key, then paste "
                "it into the 'API Token' field under the SteamGridDB menu. You "
                "can close this window once it's saved."
            )
        elif not ok and not self._navigated:
            self._status.setText("Could not load SteamGridDB — check your connection.")

    def cancel(self):
        self.reject()

    def closeEvent(self, event):
        self._timer.stop()
        self._view.stop()
        super().closeEvent(event)
