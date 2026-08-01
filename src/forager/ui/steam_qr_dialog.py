"""Pop-up Steam QR sign-in: run DepotDownloader ``-qr`` and show the code.

The QR code is re-rendered from DepotDownloader's ASCII-art output (QRCoder
draws each module as two characters), so no QR library is needed. Accounts
without the Steam mobile app use the username/password flow instead.
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from forager.library import steam
from forager.ui.theme import C
from forager.ui.steam_login_worker import SteamQrWorker

_QR_SIZE = 240

_DIALOG_QSS = f"""
QDialog {{ background-color: {C.BG}; }}
QLabel {{ color: {C.TEXT}; background: transparent; }}
QLabel#qrStatus {{ color: {C.TEXT_DIM}; font-size: 11px; }}
QPushButton {{ background-color: {C.COLOR_2}; color: {C.TEXT};
 border: 1px solid {C.COLOR_3}; border-radius: {C.RADIUS}px; padding: 6px 16px; }}
QPushButton:hover {{ background-color: {C.COLOR_3}; }}
QPushButton:disabled {{ color: {C.TEXT_DIM}; }}
"""


def qr_grid_to_pixmap(grid, target: int = _QR_SIZE) -> QPixmap:
    """Render a boolean QR grid (True = dark) into a smooth QPixmap."""
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    if not width or not height:
        return QPixmap()
    img = QImage(width, height, QImage.Format.Format_Grayscale8)
    for y, row in enumerate(grid):
        for x, dark in enumerate(row):
            img.setPixel(x, y, 0 if dark else 255)
    scaled = img.scaled(
        target, target,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return QPixmap.fromImage(scaled)


class SteamQrDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in with Steam")
        self.setModal(True)
        self.setStyleSheet(_DIALOG_QSS)
        self.setMinimumWidth(360)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        heading = QLabel("Sign in with Steam")
        heading.setStyleSheet("font-size: 15px; font-weight: 600;")
        lay.addWidget(heading)

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setFixedSize(_QR_SIZE + 16, _QR_SIZE + 16)
        lay.addWidget(self._qr_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self._status = QLabel(
            "Scan this code with the Steam mobile app to approve the sign-in."
        )
        self._status.setObjectName("qrStatus")
        self._status.setWordWrap(True)
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._status)

        row = QHBoxLayout()
        row.addStretch(1)
        self._no_phone_btn = QPushButton("No Steam app? Use username & password")
        self._no_phone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._no_phone_btn.clicked.connect(self.reject)
        row.addWidget(self._no_phone_btn)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)
        row.addWidget(self._cancel_btn)
        lay.addLayout(row)

        self._worker = SteamQrWorker(self)
        self._worker.qr_changed.connect(self._on_qr)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    # -- worker wiring ------------------------------------------------

    def _on_qr(self, art_lines):
        pixmap = qr_grid_to_pixmap(steam.parse_qr_art(art_lines))
        if not pixmap.isNull():
            self._qr_label.setPixmap(pixmap)
        self._status.setText(
            "Scan this code with the Steam mobile app to approve the sign-in."
        )

    def _on_done(self, ok: bool, detail: str):
        if not self.isVisible():
            return
        if ok:
            try:
                steam.set_qr_username(detail)
            except Exception as e:
                self._status.setText(f"Signed in, but could not store the session: {e}")
                return
            self._status.setText(f"Signed in as {detail} — session saved.")
            self.accept()
        else:
            self._status.setText(detail or "Sign-in failed.")
            self._cancel_btn.setEnabled(True)

    def _on_cancel(self):
        self._cancel_btn.setEnabled(False)
        self._worker.cancel()
        self.reject()

    # -- cleanup ------------------------------------------------------

    def cancel(self):
        self._worker.cancel()

    def closeEvent(self, event):
        self._worker.cancel()
        self._worker.wait(3000)
        super().closeEvent(event)
