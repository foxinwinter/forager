"""Sidebar download box and Downloads page, styled like Steam's SpaceTheme
download bar: a compact card above the user panel with a 4px rounded accent
progress bar. The box is only visible while a download is active; clicking it
opens the built-in Downloads page.
"""
from __future__ import annotations
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout,
)

from forager.ui.theme import C
from forager.ui.icons import load_icon

_SPEED_QSS = f"color: #b8bcbf; font-size: 11px; background: transparent;"


def format_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


class ProgressBar(QWidget):
    """SpaceTheme-style 4px bar: background track with a rounded accent fill."""

    def __init__(self, height: int = 4, parent=None):
        super().__init__(parent)
        self._height = height
        self._value = 0.0
        self.setFixedHeight(height)
        self.setMinimumWidth(40)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(100.0, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = r.height() / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(C.BG))
        painter.drawRoundedRect(r, radius, radius)
        if self._value > 0:
            width = max(r.height(), r.width() * self._value / 100.0)
            painter.setBrush(QColor(C.ACCENT_1))
            painter.drawRoundedRect(
                QRectF(r.left(), r.top(), width, r.height()), radius, radius
            )
        painter.end()


class DownloadBox(QFrame):
    """Compact sidebar card shown only while a download is active."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("downloadBox")
        self.setStyleSheet(
            f"#downloadBox {{ background-color: {C.COLOR_2}; border: none;"
            f"border-radius: {C.RADIUS}px; }}"
            f"#downloadBox:hover {{ background-color: {C.COLOR_3}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(6)
        self._name = QLabel("Downloading")
        self._name.setStyleSheet(
            f"color: {C.TEXT}; font-size: 12px; font-weight: 600; background: transparent;"
        )
        self._percent = QLabel("0%")
        self._percent.setStyleSheet(
            f"color: {C.ACCENT_2}; font-size: 12px; font-weight: 600; background: transparent;"
        )
        top.addWidget(self._name)
        top.addStretch(1)
        top.addWidget(self._percent)
        layout.addLayout(top)

        self._bar = ProgressBar(parent=self)
        layout.addWidget(self._bar)

        self._detail = QLabel("")
        self._detail.setStyleSheet(_SPEED_QSS)
        layout.addWidget(self._detail)

        self.hide()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def begin(self, name: str) -> None:
        self._name.setText(name)
        self._percent.setText("0%")
        self._bar.set_value(0)
        self._detail.setText("")
        self.show()

    def set_progress(self, progress) -> None:
        percent = f"{progress.percent:.0f}%"
        self._percent.setText(percent)
        self._bar.set_value(progress.percent)
        if progress.stage.lower() == "downloading":
            bits = [f"{format_size(progress.done)} / {format_size(progress.total)}"]
            if progress.speed > 0:
                bits.append(f"{format_size(progress.speed)}/s")
            self._detail.setText(" \u00b7 ".join(bits))
        else:
            self._detail.setText(f"{progress.stage}\u2026")

    def hide_download(self) -> None:
        self.hide()


class DownloadsPage(QWidget):
    """Steam-style download manager page (opened from the sidebar box)."""

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {C.BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)

        header = QLabel("Downloads")
        header.setFont(QFont("Roboto", 22, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        layout.addWidget(header)

        self._card = QFrame()
        self._card.setObjectName("downloadCard")
        self._card.setStyleSheet(
            f"#downloadCard {{ background-color: {C.COLOR_2}; border: none;"
            f"border-radius: {C.RADIUS}px; }}"
        )
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)
        self._icon = QLabel()
        self._icon.setPixmap(load_icon("download", C.ACCENT_1).pixmap(20, 20))
        self._icon.setFixedSize(28, 28)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet(
            f"background-color: {C.COLOR_3}; border-radius: 6px;"
        )
        self._title = QLabel("Proton Experimental")
        self._title.setStyleSheet(
            f"color: {C.TEXT}; font-size: 14px; font-weight: 600; background: transparent;"
        )
        self._cancel = QPushButton("Cancel")
        self._cancel.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_3}; color: {C.TEXT};"
            f"border: none; border-radius: {C.RADIUS}px; padding: 5px 14px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_1}; }}"
        )
        self._cancel.clicked.connect(self.cancel_requested)
        top.addWidget(self._icon)
        top.addWidget(self._title)
        top.addStretch(1)
        top.addWidget(self._cancel)
        card_layout.addLayout(top)

        self._status = QLabel("")
        self._status.setStyleSheet(
            f"color: {C.TEXT_MUTED}; font-size: 12px; background: transparent;"
        )
        card_layout.addWidget(self._status)

        self._bar = ProgressBar(height=6, parent=self)
        card_layout.addWidget(self._bar)

        layout.addWidget(self._card)

        self._empty = QLabel("No downloads in progress")
        self._empty.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 13px; background: transparent;"
        )
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty, stretch=1)

        self.set_idle()

    def set_idle(self) -> None:
        self._card.hide()
        self._empty.show()

    def begin(self, name: str) -> None:
        self._title.setText(name)
        self._status.setText("Waiting to start\u2026")
        self._bar.set_value(0)
        self._cancel.show()
        self._card.show()
        self._empty.hide()

    def set_progress(self, progress) -> None:
        self._bar.set_value(progress.percent)
        if progress.stage.lower() == "downloading":
            bits = [f"Downloading \u00b7 {progress.percent:.0f}%",
                    f"{format_size(progress.done)} / {format_size(progress.total)}"]
            if progress.speed > 0:
                bits.append(f"{format_size(progress.speed)}/s")
            self._status.setText(" \u00b7 ".join(bits))
        else:
            self._status.setText(f"{progress.stage}\u2026 \u00b7 {progress.percent:.0f}%")

    def complete(self, version: str = "") -> None:
        self._bar.set_value(100)
        self._cancel.hide()
        if version:
            self._status.setText(f"Completed\u2014Proton {version}")
        else:
            self._status.setText("Completed")
        self._card.show()
        self._empty.hide()

    def failed(self, error: str) -> None:
        self._cancel.hide()
        self._status.setText(f"Failed: {error}")
        self._card.show()
        self._empty.hide()

    def cancelled(self) -> None:
        self._cancel.hide()
        self._status.setText("Download cancelled")
        self._card.show()
        self._empty.hide()
