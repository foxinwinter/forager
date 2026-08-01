"""Steam sign-in via the official Steam login page in an embedded webview.

We don't render QR codes ourselves: Steam's own login page handles every auth
path (password + Steam Guard, email codes, or the mobile app's crisp QR) and
the resulting session lives in the webview's persistent cookie store. Sign-in
is detected by watching for the ``steamLoginSecure`` cookie — its value carries
the account's SteamID, which is resolved to an account name and stored in the
keyring.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from forager.library import steam
from forager.ui.theme import C

LOGIN_URL = "https://login.steampowered.com/"
STORE_URL = "https://store.steampowered.com/"

_NAME_JS = """
(function () {
    var sels = [
        ".account_pulldown_persona",
        ".account_pulldown_persona_name",
        "#account_pulldown",
        ".persona_name",
    ];
    for (var i = 0; i < sels.length; i++) {
        var el = document.querySelector(sels[i]);
        var t = el && el.textContent.trim();
        if (t) { return t; }
    }
    return "";
})()
"""

_DIALOG_QSS = f"""
QDialog {{ background-color: {C.BG}; }}
QLabel#steamWebStatus {{ color: {C.TEXT_DIM}; font-size: 11px;
 background: {C.COLOR_2}; padding: 6px 12px; }}
QLabel#steamWebStatus[loggedIn="true"] {{ color: {C.ACCENT_1}; }}
"""


def clear_web_cookies() -> None:
    """Drop Steam's web session cookies so the login dialog starts fresh."""
    QWebEngineProfile.defaultProfile().cookieStore().deleteAllCookies()


class SteamWebLoginDialog(QDialog):
    login_succeeded = Signal(str)
    _resolved_name = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in with Steam")
        self.setModal(True)
        self.resize(900, 640)
        self.setMinimumSize(640, 480)
        self.setStyleSheet(_DIALOG_QSS)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._view = QWebEngineView(self)
        lay.addWidget(self._view)

        self._status = QLabel(
            "Sign in on this page — Steam handles password, Steam Guard and "
            "mobile-app QR for you. You can close this window once you're in."
        )
        self._status.setObjectName("steamWebStatus")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._resolved_steamid: str | None = None
        self._fallback_pending = False
        self._resolved_name.connect(self._on_resolved)

        store = self._view.page().profile().cookieStore()
        store.cookieAdded.connect(self._on_cookie)
        store.loadAllCookies()
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.load(QUrl(LOGIN_URL))

    # -- worker wiring ------------------------------------------------

    @staticmethod
    def _cookie_str(v):
        return v if isinstance(v, str) else bytes(v).decode("utf-8", "replace")

    def _on_cookie(self, cookie):
        if self._cookie_str(cookie.name()) != "steamLoginSecure":
            return
        if "steampowered.com" not in self._cookie_str(cookie.domain()):
            return
        steamid = steam.steamid_from_cookie(self._cookie_str(cookie.value()))
        if not steamid or steamid == self._resolved_steamid:
            return
        self._resolved_steamid = steamid
        threading.Thread(target=self._lookup, args=(steamid,), daemon=True).start()

    def _lookup(self, steamid: str):
        name = steam.account_name_from_steamid(steamid)
        self._resolved_name.emit(name or "")

    def _on_resolved(self, name: str):
        if (name or "").strip():
            self._finalize(name.strip())
            return
        # The public profile XML is sometimes rate-limited; fall back to
        # reading the persona name from the logged-in store header.
        if not self._fallback_pending:
            self._fallback_pending = True
            self._status.setText("Signed in — reading your account name…")
            self._view.setUrl(QUrl(STORE_URL))

    def _on_load_finished(self, ok: bool):
        if self._fallback_pending and ok:
            self._view.page().runJavaScript(_NAME_JS, self._on_js_name)
        elif not ok and not self._resolved_steamid:
            self._status.setText("Could not load the Steam login page — check your connection.")

    def _on_js_name(self, name):
        self._fallback_pending = False
        self._finalize((name or "").strip() or self._resolved_steamid or "")

    def _finalize(self, account: str):
        account = account.strip()
        if not account:
            self._status.setText(
                "Signed in — but the account name could not be read. "
                "Close this window to finish."
            )
            return
        try:
            steam.set_web_username(account)
        except Exception as e:
            self._status.setText(f"Signed in as {account}, but could not store the session: {e}")
            return
        self._status.setText(f"Signed in as {account} — session saved. You can close this window.")
        self._status.setProperty("loggedIn", True)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self.login_succeeded.emit(account)

    # -- cleanup ------------------------------------------------------

    def cancel(self):
        self.reject()

    def closeEvent(self, event):
        self._view.stop()
        super().closeEvent(event)
