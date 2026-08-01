"""Background Steam login validation via DepotDownloader.

Credentials are validated on a ``QThread`` so the UI stays responsive; Steam
Guard codes are requested on the GUI thread and fed back through a queue.
"""
from __future__ import annotations
import queue
import threading
from PySide6.QtCore import QThread, Signal


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


class SteamQrWorker(QThread):
    """Runs DepotDownloader ``-qr`` on a thread, feeding the ASCII-art QR
    lines to the GUI via ``qr_changed`` and reporting the result with ``done``."""

    qr_changed = Signal(list)
    done = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = threading.Event()

    def run(self):
        from forager.library import steam

        def qr_callback(art_lines):
            self.qr_changed.emit(list(art_lines))

        try:
            ok, detail = steam.login_with_qr(qr_callback, cancel_event=self._cancel)
        except Exception as e:
            ok, detail = False, str(e)
        self.done.emit(ok, detail)

    def cancel(self):
        self._cancel.set()
