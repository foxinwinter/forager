"""Sidebar download box and Downloads page, styled like Steam's SpaceTheme
download bar and downloads page (src/css/steam/sidebar.css + downloadPage.css).

The sidebar ``DownloadBox`` is a compact card above the user panel (COLOR_2,
4px rounded accent bar) visible only while a download is active; clicking it
opens the built-in Downloads page. That page mirrors Steam's download page:
a full-width banner with a right-side fade to COLOR_2, a stats row with the
accent-coloured download speed, and an Updates list.
"""
from __future__ import annotations
import shutil
from PySide6.QtCore import Qt, QRectF, Signal, QSize
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout,
)

from forager.ui.theme import C
from forager.ui.icons import load_icon
from forager.utils.paths import games_dir

_SPEED_QSS = f"color: #b8bcbf; font-size: 11px; background: transparent;"
_DIM_TEXT_QSS = "color: #b8bcbf; background: transparent;"


def format_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def _format_eta(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


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


class _Banner(QWidget):
    """Full-width 'installing now' banner: art background fading to COLOR_2 on
    the right (SpaceTheme downloadPage.css), title/status over the art, and a
    4px accent progress bar flush along the bottom edge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(230)
        self._watermark = load_icon("download", C.TEXT).pixmap(170, 170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        info = QHBoxLayout()
        info.setContentsMargins(28, 26, 28, 0)
        info.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(4)
        self._title = QLabel("")
        self._title.setStyleSheet(
            f"color: {C.TEXT}; font-size: 20px; font-weight: 700; background: transparent;"
        )
        self._status = QLabel("")
        self._status.setStyleSheet(
            f"color: {C.ACCENT_1}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        col.addWidget(self._title)
        col.addWidget(self._status)
        info.addLayout(col)
        info.addStretch(1)
        layout.addLayout(info)
        layout.addStretch(1)

        self._bar = ProgressBar(height=4, parent=self)
        layout.addWidget(self._bar)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_bar(self, percent: float) -> None:
        self._bar.set_value(percent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        base = QLinearGradient(0, 0, 0, h)
        base.setColorAt(0.0, QColor("#222833"))
        base.setColorAt(1.0, QColor("#12161c"))
        painter.fillRect(0, 0, w, h, base)

        side = min(w, h) // 2
        if not self._watermark.isNull():
            painter.setOpacity(0.10)
            painter.drawPixmap(
                (w - side) // 2, int(h * 0.42) - side // 2, side, side, self._watermark
            )
            painter.setOpacity(1.0)

        fade = QLinearGradient(0, 0, w, 0)
        fade.setColorAt(0.15, QColor(C.COLOR_2).withAlpha(0))
        fade.setColorAt(0.90, QColor(C.COLOR_2))
        painter.fillRect(0, 0, w, h, fade)
        painter.end()


class _StatItem(QWidget):
    """Stats-row entry: accent icon chip + caption + big value (accent for the
    download speed, per SpaceTheme downloadPage.css)."""

    def __init__(self, icon_name: str, caption: str, accent: bool = False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        chip = QLabel()
        chip.setPixmap(load_icon(icon_name, C.ACCENT_1).pixmap(18, 18))
        chip.setFixedSize(36, 36)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setStyleSheet(f"background-color: {C.COLOR_3}; border-radius: 8px;")

        text = QVBoxLayout()
        text.setSpacing(1)
        cap = QLabel(caption)
        cap.setStyleSheet(f"color: #b8bcbf; font-size: 11px; background: transparent;")
        self._value = QLabel("\u2014")
        self._value.setStyleSheet(
            f"color: {C.ACCENT_1 if accent else C.TEXT}; font-size: 15px;"
            f"font-weight: 700; background: transparent;"
        )
        text.addWidget(cap)
        text.addWidget(self._value)

        lay.addWidget(chip)
        lay.addLayout(text)
        lay.addStretch(1)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class DownloadsPage(QWidget):
    """Steam-style download manager page (opened from the sidebar box)."""

    cancel_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {C.BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 0)
        title = QLabel("Downloads")
        title.setFont(QFont("Roboto", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        gear = QPushButton()
        gear.setIcon(load_icon("settings", C.TEXT_DIM))
        gear.setIconSize(QSize(18, 18))
        gear.setFixedSize(28, 28)
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.setToolTip("Download settings")
        gear.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 6px;"
            f"padding: 0; }}"
            f"QPushButton:hover {{ background: transparent; }}"
        )
        gear.setIcon(load_icon("settings", C.TEXT))
        gear.clicked.connect(self.settings_requested)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(gear)
        layout.addLayout(header)

        self._banner = _Banner()
        layout.addWidget(self._banner)

        stats = QHBoxLayout()
        stats.setContentsMargins(12, 4, 12, 0)
        stats.setSpacing(28)
        self._speed_stat = _StatItem("download", "Download speed", accent=True)
        self._time_stat = _StatItem("clock-rotate-right", "Time remaining")
        self._space_stat = _StatItem("floppy-disk", "Available space")
        for stat in (self._speed_stat, self._time_stat, self._space_stat):
            stats.addWidget(stat)
        stats.addStretch(1)
        layout.addLayout(stats)

        queue = QVBoxLayout()
        queue.setContentsMargins(12, 8, 12, 0)
        queue.setSpacing(8)
        qheader = QLabel("Updates")
        qheader.setFont(QFont("Roboto", 15, QFont.Weight.Bold))
        qheader.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        queue.addWidget(qheader)

        self._item = QFrame()
        self._item.setObjectName("queueItem")
        self._item.setStyleSheet(
            f"#queueItem {{ background-color: {C.COLOR_2}; border: none;"
            f"border-radius: {C.RADIUS}px; }}"
        )
        item_lay = QHBoxLayout(self._item)
        item_lay.setContentsMargins(16, 12, 16, 12)
        item_lay.setSpacing(14)

        chip = QLabel()
        chip.setPixmap(load_icon("download", C.ACCENT_2).pixmap(20, 20))
        chip.setFixedSize(34, 34)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setStyleSheet(f"background-color: {C.COLOR_3}; border-radius: 8px;")
        item_lay.addWidget(chip)

        col = QVBoxLayout()
        col.setSpacing(2)
        self._item_name = QLabel("")
        self._item_name.setStyleSheet(
            f"color: {C.TEXT}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        self._item_status = QLabel("")
        self._item_status.setStyleSheet(_DIM_TEXT_QSS)
        col.addWidget(self._item_name)
        col.addWidget(self._item_status)
        item_lay.addLayout(col)
        item_lay.addStretch(1)

        self._item_bar = ProgressBar(height=4, parent=self)
        self._item_bar.setFixedWidth(220)
        item_lay.addWidget(self._item_bar)

        self._item_cancel = QPushButton("Cancel")
        self._item_cancel.setStyleSheet(
            f"QPushButton {{ background-color: {C.COLOR_3}; color: {C.TEXT};"
            f"border: none; border-radius: {C.RADIUS}px; padding: 5px 14px; }}"
            f"QPushButton:hover {{ background-color: {C.COLOR_1}; }}"
        )
        self._item_cancel.clicked.connect(self.cancel_requested)
        item_lay.addWidget(self._item_cancel)
        queue.addWidget(self._item)

        self._empty = QLabel("No active downloads")
        self._empty.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 13px; background: transparent;"
        )
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        queue.addWidget(self._empty)

        layout.addLayout(queue)
        layout.addStretch(1)
        self.set_idle()

    def _refresh_space(self) -> None:
        try:
            free = shutil.disk_usage(str(games_dir())).free
        except OSError:
            free = 0
        self._space_stat.set_value(format_size(free) if free else "\u2014")

    def set_idle(self) -> None:
        self._banner.hide()
        self._item.hide()
        self._empty.show()
        self._speed_stat.set_value("\u2014")
        self._time_stat.set_value("\u2014")
        self._refresh_space()

    def begin(self, name: str) -> None:
        self._banner.show()
        self._item.show()
        self._empty.hide()
        self._banner.set_title(name)
        self._banner.set_status("Waiting to start\u2026")
        self._banner.set_bar(0)
        self._item_name.setText(name)
        self._item_status.setText("Waiting to start\u2026")
        self._item_bar.set_value(0)
        self._item_cancel.show()
        self._speed_stat.set_value("\u2014")
        self._time_stat.set_value("\u2014")
        self._refresh_space()

    def set_progress(self, progress) -> None:
        status = (
            f"{progress.stage}\u2026 \u00b7 {progress.percent:.0f}%"
            if progress.stage.lower() != "downloading"
            else f"Downloading \u00b7 {progress.percent:.0f}%"
        )
        self._banner.set_status(status)
        self._banner.set_bar(progress.percent)
        self._item_status.setText(status)
        self._item_bar.set_value(progress.percent)

        if progress.stage.lower() == "downloading" and progress.speed > 0:
            self._speed_stat.set_value(f"{format_size(progress.speed)}/s")
            remaining = progress.total - progress.done
            self._time_stat.set_value(
                _format_eta(remaining / progress.speed) if remaining > 0 else "\u2014"
            )
        else:
            self._speed_stat.set_value("\u2014")
            self._time_stat.set_value("\u2014")

    def _finish(self, status: str) -> None:
        self._item_cancel.hide()
        self._banner.set_status(status)
        self._banner.set_bar(100)
        self._item_status.setText(status)
        self._item_bar.set_value(100)
        self._speed_stat.set_value("\u2014")
        self._time_stat.set_value("\u2014")

    def complete(self, version: str = "") -> None:
        self._finish(f"Completed\u2014{version}" if version else "Completed")

    def failed(self, error: str) -> None:
        self._finish(f"Failed: {error}")

    def cancelled(self) -> None:
        self._finish("Download cancelled")
