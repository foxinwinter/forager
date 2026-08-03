"""Native Steam sign-in dialog (QR + password/Steam Guard) — no webview.

Steam's own login page polls the auth session over a WebSocket that hangs in
QtWebEngine, so the login happens here, natively, against Steam's
``IAuthenticationService`` API (see ``forager.steam.auth``). The QR
code is rendered locally (white background, black modules, exactly like
Steam's website) and the Steam Guard code entry reuses the same API.
"""
from __future__ import annotations

import queue
import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
)

try:
    import qrcode as _qrcode
except Exception:
    _qrcode = None

from forager.steam import account, auth
from forager.steam.auth import SteamAuthError, GUARD_EMAIL_CODE
from forager.ui.theme import C

_QR_PIXEL_SIZE = 256

_INPUT_QSS = f"""
QLineEdit {{
    background-color: {C.COLOR_2}; color: {C.TEXT};
    border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px;
    padding: 5px 8px;
}}
QLineEdit:focus {{ border: 1px solid {C.ACCENT_1}; }}
"""

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

_STATUS_QSS = f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent;"
_TITLE_QSS = f"color: {C.TEXT}; font-size: 14px; font-weight: 600; background: transparent;"
_LINK_QSS = f"""
QPushButton {{ background: transparent; color: {C.ACCENT_1}; border: none;
 padding: 2px 0; text-align: left; }}
QPushButton:hover {{ color: {C.ACCENT_2}; }}
"""


class SteamAuthWorker(QThread):
    """Runs one Steam auth flow off the GUI thread."""

    status = Signal(str)
    qr_ready = Signal(str)
    code_requested = Signal(int, str)  # code_type, message
    code_rejected = Signal(str)
    done = Signal(bool, str)

    def __init__(self, method: str, username: str = "", password: str = "", parent=None):
        super().__init__(parent)
        self._method = method  # "qr" or "password"
        self._username = username
        self._password = password
        self._codes: queue.Queue = queue.Queue()
        self._cancel = threading.Event()

    # -- public API (GUI thread) ---------------------------------------

    def submit_code(self, code: str):
        self._codes.put(code.strip())

    def cancel(self):
        self._cancel.set()
        self._codes.put(None)

    # -- worker body ----------------------------------------------------

    def run(self):
        try:
            self._run_flow()
        except SteamAuthError as e:
            self.done.emit(False, str(e))
        except Exception as e:
            self.done.emit(False, f"Unexpected error: {e}")

    def _run_flow(self):
        if self._method == "qr":
            session = auth.start_qr_session()
        else:
            if not self._username or not self._password:
                self.done.emit(False, "Enter your Steam account name and password.")
                return
            session = auth.start_credentials_session(self._username, self._password)

        if self._method == "qr" and session.challenge_url:
            self.qr_ready.emit(session.challenge_url)

        self._handle_confirmations(session)
        result = self._poll_until_done(session)

        steamid = (
            result["steamid"]
            or auth.steamid_from_refresh_token(result["refresh_token"])
        )
        login_secure = auth.finalize_login(result["refresh_token"], steamid)
        steamid = steamid or account.steamid_from_cookie(login_secure)

        account_name = result["account_name"]
        if not account_name and steamid:
            account_name = account.account_name_from_steamid(steamid)
        account_name = (account_name or self._username or steamid or "").strip() or steamid or ""

        account.set_steam_session(
            account_name,
            method=self._method,
            password=self._password if self._method == "password" else None,
            steamid=steamid,
            login_secure=login_secure,
        )
        self.done.emit(True, account_name)

    def _handle_confirmations(self, session):
        if session.code_types:
            self._request_code(session.code_types[0])
        elif session.needs_approval:
            self.status.emit(
                "Approve the sign-in in the Steam mobile app — waiting…"
            )

    def _request_code(self, code_type: int):
        if code_type == GUARD_EMAIL_CODE:
            message = "Enter the Steam Guard code sent to your email."
        else:
            message = "Enter the Steam Guard code from the Steam mobile app."
        self.code_requested.emit(code_type, message)

    def _poll_until_done(self, session):
        client_id = session.client_id
        request_id = session.request_id
        code_types = session.code_types
        steamid = session.steamid
        code_pending = False
        code_attempts = 0
        while not self._cancel.is_set():
            code = self._drain_code()
            if code is not None:
                code_type = code_types[0] if code_types else GUARD_EMAIL_CODE
                auth.update_session_with_guard_code(client_id, code, code_type, steamid)
                code_pending = True
                code_attempts = 0
                self.status.emit("Checking your code…")

            result = auth.poll_session(client_id, request_id)
            if result.expired:
                raise SteamAuthError("That sign-in link expired — start again or refresh the code.")
            if result.authorized:
                return {
                    "steamid": steamid or auth.steamid_from_refresh_token(result.refresh_token),
                    "account_name": result.account_name,
                    "refresh_token": result.refresh_token,
                }
            if result.new_client_id:
                client_id = result.new_client_id

            if code_pending:
                code_attempts += 1
                if code_attempts >= 4:
                    self.code_rejected.emit("That code wasn't accepted — try again.")
                    code_pending = False
            self._cancel.wait(float(session.interval or 5))

        raise SteamAuthError("Sign-in cancelled.")

    def _drain_code(self):
        try:
            return self._codes.get_nowait()
        except queue.Empty:
            return None


class SteamAuthDialog(QDialog):
    """QR-first Steam sign-in with a username/password fallback."""

    login_succeeded = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in with Steam")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setStyleSheet(f"QDialog {{ background-color: {C.BG}; }}")

        self._worker: SteamAuthWorker | None = None
        self._login_secure: str | None = None
        self._steamid: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        self._title = QLabel("Sign in with Steam")
        self._title.setStyleSheet(_TITLE_QSS)
        lay.addWidget(self._title)

        # -- QR mode ---------------------------------------------------
        self._qr_box = QVBoxLayout()
        self._qr_box.setSpacing(8)

        self._qr_image = QLabel()
        self._qr_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_image.setMinimumSize(_QR_PIXEL_SIZE, _QR_PIXEL_SIZE)
        self._qr_box.addWidget(self._qr_image)

        self._qr_hint = QLabel(
            "Open the Steam mobile app → Scan this QR code to approve the sign-in."
        )
        self._qr_hint.setWordWrap(True)
        self._qr_hint.setStyleSheet(_STATUS_QSS)
        self._qr_box.addWidget(self._qr_hint)

        self._qr_refresh_btn = QPushButton("Refresh QR code")
        self._qr_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._qr_refresh_btn.setStyleSheet(_SECONDARY_BTN_QSS)
        self._qr_refresh_btn.clicked.connect(self._refresh_qr)
        self._qr_box.addWidget(self._qr_refresh_btn)

        self._qr_password_link = QPushButton("Use password instead")
        self._qr_password_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._qr_password_link.setStyleSheet(_LINK_QSS)
        self._qr_password_link.clicked.connect(self._show_password_mode)
        self._qr_box.addWidget(self._qr_password_link)
        lay.addLayout(self._qr_box)

        # -- password mode ---------------------------------------------
        self._pw_box = QVBoxLayout()
        self._pw_box.setSpacing(8)

        self._pw_user = QLineEdit()
        self._pw_user.setPlaceholderText("Steam account name")
        self._pw_user.setStyleSheet(_INPUT_QSS)
        self._pw_box.addWidget(self._pw_user)

        self._pw_pass = QLineEdit()
        self._pw_pass.setPlaceholderText("Password")
        self._pw_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_pass.setStyleSheet(_INPUT_QSS)
        self._pw_box.addWidget(self._pw_pass)

        self._pw_signin_btn = QPushButton("Sign in")
        self._pw_signin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pw_signin_btn.setStyleSheet(_PRIMARY_BTN_QSS)
        self._pw_signin_btn.clicked.connect(self._start_password)
        self._pw_box.addWidget(self._pw_signin_btn)

        self._pw_qr_link = QPushButton("Use QR instead")
        self._pw_qr_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pw_qr_link.setStyleSheet(_LINK_QSS)
        self._pw_qr_link.clicked.connect(self._show_qr_mode)
        self._pw_box.addWidget(self._pw_qr_link)
        lay.addLayout(self._pw_box)

        # -- Steam Guard code row (shared) ------------------------------
        self._code_row = QHBoxLayout()
        self._code_edit = QLineEdit()
        self._code_edit.setPlaceholderText("Steam Guard code")
        self._code_edit.setStyleSheet(_INPUT_QSS)
        self._code_edit.returnPressed.connect(self._submit_code)
        self._code_edit.setEnabled(False)
        self._code_row.addWidget(self._code_edit, 1)

        self._code_btn = QPushButton("Submit")
        self._code_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._code_btn.setStyleSheet(_PRIMARY_BTN_QSS)
        self._code_btn.setEnabled(False)
        self._code_btn.clicked.connect(self._submit_code)
        self._code_row.addWidget(self._code_btn)
        lay.addLayout(self._code_row)

        self._code_hint = QLabel()
        self._code_hint.setWordWrap(True)
        self._code_hint.setStyleSheet(_STATUS_QSS)
        lay.addWidget(self._code_hint)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setStyleSheet(_STATUS_QSS)
        lay.addWidget(self._status)
        lay.addStretch(1)

        self._show_qr_mode()
        self._start_qr()

    # -- mode switching -------------------------------------------------

    def _show_qr_mode(self):
        for w in (self._pw_user, self._pw_pass, self._pw_signin_btn, self._pw_qr_link):
            w.setVisible(False)
        for w in (self._qr_image, self._qr_hint, self._qr_refresh_btn, self._qr_password_link):
            w.setVisible(True)

    def _show_password_mode(self):
        for w in (self._qr_image, self._qr_hint, self._qr_refresh_btn, self._qr_password_link):
            w.setVisible(False)
        for w in (self._pw_user, self._pw_pass, self._pw_signin_btn, self._pw_qr_link):
            w.setVisible(True)
        self._pw_user.setFocus()

    # -- worker lifecycle -----------------------------------------------

    def _spawn_worker(self, method: str, username: str = "", password: str = ""):
        self._cancel_worker()
        self._set_code_entry_enabled(False)
        self._code_hint.clear()
        worker = SteamAuthWorker(method, username, password, self)
        worker.status.connect(self._status.setText)
        worker.qr_ready.connect(self._on_qr_ready)
        worker.code_requested.connect(self._on_code_requested)
        worker.code_rejected.connect(self._on_code_rejected)
        worker.done.connect(self._on_done)
        self._worker = worker
        worker.start()

    def _cancel_worker(self):
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.cancel()
            worker.wait(8000)
        self._worker = None

    def _start_qr(self):
        self._qr_image.clear()
        self._status.setText("Starting a secure sign-in…")
        self._spawn_worker("qr")

    def _refresh_qr(self):
        self._start_qr()

    def _start_password(self):
        self._spawn_worker(
            "password",
            username=self._pw_user.text().strip(),
            password=self._pw_pass.text(),
        )

    # -- worker signals ------------------------------------------------

    def _on_qr_ready(self, url: str):
        self._qr_image.setPixmap(self._qr_pixmap(url))
        self._status.setText("Scan the code with the Steam mobile app to approve the sign-in.")

    def _on_code_requested(self, code_type: int, message: str):
        self._code_hint.setText(message)
        self._set_code_entry_enabled(True)
        self._code_edit.setFocus()

    def _on_code_rejected(self, message: str):
        self._code_hint.setText(message)
        self._code_edit.clear()
        self._set_code_entry_enabled(True)
        self._code_edit.setFocus()

    def _submit_code(self):
        code = self._code_edit.text().strip()
        if not code or self._worker is None:
            return
        self._set_code_entry_enabled(False)
        self._status.setText("Submitting your code…")
        self._worker.submit_code(code)

    def _set_code_entry_enabled(self, enabled: bool):
        self._code_edit.setEnabled(enabled)
        self._code_btn.setEnabled(enabled)

    def _on_done(self, ok: bool, account: str):
        if not ok:
            self._set_code_entry_enabled(False)
            self._status.setText(account)
            self._status.setStyleSheet(
                f"color: {C.RED}; font-size: 11px; background: transparent;"
            )
            return
        self._status.setStyleSheet(f"color: {C.ACCENT_1}; font-size: 11px; background: transparent;")
        self._status.setText(f"Signed in as {account}.")
        self.login_succeeded.emit(account)
        self.accept()

    # -- helpers -------------------------------------------------------

    @staticmethod
    def _qr_pixmap(url: str):
        if _qrcode is None:
            return QPixmap()
        qr = _qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
        pix = QPixmap.fromImage(qimage)
        return pix.scaled(
            _QR_PIXEL_SIZE, _QR_PIXEL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def cancel(self):
        self._cancel_worker()
        self.reject()

    def closeEvent(self, event):
        self._cancel_worker()
        super().closeEvent(event)
