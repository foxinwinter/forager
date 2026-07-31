from __future__ import annotations
import threading
from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox,
    QPushButton, QGridLayout, QScrollArea, QStackedWidget, QApplication,
    QMenuBar,
)

from gamehub.core.game import Game
from gamehub.core.config import settings
from gamehub.library.scanner import scan_all
from gamehub.library.launcher import launch
from gamehub.core.controller import ControllerPoller
from gamehub.services.art import bytes_to_pixmap
from gamehub.ui.theme import C
from gamehub.ui.sidebar import Sidebar
from gamehub.ui.game_card import GameCard, CARD_W, CARD_H
from gamehub.ui.gamepage import GamePage
from gamehub.ui.settings import SettingsDialog


class ScanWorker(QThread):
    done = Signal(object)

    def run(self):
        games = scan_all()
        if not self.isInterruptionRequested():
            self.done.emit(games)


class ProtonUpdateWorker(QThread):
    message = Signal(str)
    done = Signal(bool, str)

    def run(self):
        from gamehub.library.proton import update_proton

        try:
            update_proton(self.message.emit)
        except Exception as e:
            self.done.emit(False, str(e))
        else:
            self.done.emit(True, "")


class ArtSignals(QObject):
    grid_ready = Signal(object)
    icon_ready = Signal(object)


class HeroSignals(QObject):
    ready = Signal(object)


def _art_job(games: list[Game], signals: ArtSignals, stop_event: threading.Event):
    from gamehub.services import art
    from gamehub.library.icon_provider import load_icon_bytes

    for game in games:
        if stop_event.is_set():
            return
        data = art.load_grid_bytes(game)
        if data:
            signals.grid_ready.emit((game, data))
        if stop_event.is_set():
            return
        icon = load_icon_bytes(game)
        if icon:
            signals.icon_ready.emit((game, icon))


def _hero_job(game: Game, signals: HeroSignals, stop_event: threading.Event):
    from gamehub.services import art

    if stop_event.is_set():
        return
    data = art.load_hero_bytes(game)
    if data:
        signals.ready.emit((game, data))


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(24, 24)
        p.rotate(self._angle)
        for i in range(8):
            alpha = 255 - (i * 32)
            p.setBrush(QColor(*_hex(C.ACCENT_1), alpha))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(-3, -16, 6, 6)
            p.rotate(45)


def _hex(color: str) -> tuple:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._games: list[Game] = []
        self._cards: list[GameCard] = []
        self._card_index = 0
        self._controller = ControllerPoller(self)
        self._scan_done = False
        self._hero_done: set = set()
        self._art_stop = threading.Event()
        self._hero_stop = threading.Event()

        self._setup_ui()
        self._wire_controller()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_threads)
        QTimer.singleShot(50, self._load_games)

    # -- UI ------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle("forager")
        self.setMinimumSize(760, 480)
        self.resize(1100, 700)

        self._build_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._build_titlebar(right_layout)

        self._content = QStackedWidget()
        right_layout.addWidget(self._content, stretch=1)
        layout.addWidget(right, stretch=1)

        self._sidebar = Sidebar()
        layout.addWidget(self._sidebar)

        self._home = self._build_home()
        self._content.addWidget(self._home)

        self._gamepage = GamePage()
        self._content.addWidget(self._gamepage)

        self._sidebar.home_requested.connect(self._show_home)
        self._sidebar.game_selected.connect(self._open_game)
        self._sidebar.source_changed.connect(self._on_filter_changed)
        self._sidebar.search_changed.connect(self._on_search_changed)
        self._sidebar.update_proton_requested.connect(self._update_proton)
        self._sidebar.token_set.connect(lambda: self._status_show("SGDB token saved"))
        self._gamepage.play.connect(self._launch_game)
        self._gamepage.back_requested.connect(self._show_home)

    def _build_titlebar(self, layout):
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"background-color: {C.COLOR_1}; border-bottom: 1px solid {C.COLOR_3};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        logo = QLabel("forager")
        logo.setFont(QFont("Roboto", 16, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {C.ACCENT_1}; background: transparent;")
        lay.addWidget(logo)

        self._back_btn = self._nav_button("‹")
        self._forward_btn = self._nav_button("›")
        self._back_btn.setToolTip("Back to Library")
        self._forward_btn.setToolTip("Forward")
        self._back_btn.clicked.connect(self._show_home)
        self._forward_btn.setEnabled(False)
        lay.addWidget(self._back_btn)
        lay.addWidget(self._forward_btn)

        lay.addStretch(1)

        self._title_label = QLabel("Library")
        self._title_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 13px; background: transparent;")
        lay.addWidget(self._title_label)

        lay.addStretch(1)

        self._controller_hint = QLabel("")
        self._controller_hint.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 11px; background: transparent; padding: 4px 8px;"
        )
        lay.addWidget(self._controller_hint)

        layout.addWidget(bar)

    def _build_menu_bar(self):
        bar = QMenuBar(self)
        bar.setStyleSheet(
            f"QMenuBar {{ background-color: {C.BG}; color: {C.TEXT}; }}"
            f"QMenuBar::item {{ padding: 6px 12px; background: transparent; }}"
            f"QMenuBar::item:selected {{ background-color: {C.COLOR_2}; }}"
        )
        menu = bar.addMenu("forager")
        settings_action = menu.addAction("Settings…")
        settings_action.triggered.connect(self._open_settings)
        update_action = menu.addAction("Update Proton")
        update_action.triggered.connect(self._update_proton)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.close)
        self.setMenuBar(bar)

    def _open_settings(self):
        self._games_dir_before = str(settings.games_dir)
        dialog = SettingsDialog(self)
        dialog.update_proton_requested.connect(self._update_proton)
        dialog.games_dir_changed.connect(self._reload_library)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            if dialog._games_dir_edit.text() != str(self._games_dir_before):
                self._reload_library()
            else:
                self._status_show("Settings saved")

    def _reload_library(self):
        self._status_show("Rescanning library…")
        self._art_stop.set()
        self._hero_stop.set()
        self._hero_done.clear()
        self._load_games()

    def _nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {C.COLOR_2}; color: {C.TEXT};
                border: none; border-radius: {C.RADIUS}px;
                font-size: 16px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {C.COLOR_3}; }}
            QPushButton:disabled {{ color: {C.TEXT_DIM}; }}
            """
        )
        return btn

    def _build_home(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {C.BG};")
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 18, 24, 18)
        v.setSpacing(12)

        header = QLabel("Library")
        header.setFont(QFont("Roboto", 22, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        v.addWidget(header)

        self._empty_label = QLabel("No games found.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {C.TEXT_DIM}; font-size: 14px; background: transparent; padding: 60px;"
        )
        v.addWidget(self._empty_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"QScrollArea {{ background: {C.BG}; border: none; }}")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_host = QWidget()
        self._grid_host.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_host)
        v.addWidget(self._scroll, stretch=1)

        return page

    # -- game loading --------------------------------------------------

    def _load_games(self):
        self._scan_done = False
        self._worker = ScanWorker()
        self._worker.done.connect(self._on_games_scanned)
        self._worker.start()
        QTimer.singleShot(600, self._check_done)

    def _on_games_scanned(self, games: list[Game]):
        self._games = games
        self._scan_done = True

    def _check_done(self):
        if self._scan_done:
            self._finish_loading()
        else:
            QTimer.singleShot(100, self._check_done)

    def _finish_loading(self):
        self._sidebar.set_games(self._games)
        self._rebuild_cards()
        self._title_label.setText("Library")
        self._start_art_worker()

    def _start_art_worker(self):
        self._art_stop.clear()
        self._hero_stop.clear()
        self._art_signals = ArtSignals(self)
        self._art_signals.grid_ready.connect(self._on_grid_ready)
        self._art_signals.icon_ready.connect(self._on_icon_ready)
        self._art_thread = threading.Thread(
            target=_art_job,
            args=(self._games, self._art_signals, self._art_stop),
            daemon=True,
        )
        self._art_thread.start()

    def _on_grid_ready(self, payload):
        game, data = payload
        pix = bytes_to_pixmap(data)
        if pix is None:
            return
        for card in self._cards:
            if card.game == game:
                card.set_art(pix)
                break

    def _on_icon_ready(self, payload):
        game, data = payload
        pix = bytes_to_pixmap(data)
        if pix is None:
            return
        self._sidebar.set_icon(game, QIcon(pix))

    # -- card grid -----------------------------------------------------

    def _rebuild_cards(self):
        for card in self._cards:
            self._grid.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._card_index = 0

        games = self._filtered_games()
        for game in games:
            card = GameCard(game)
            card.clicked.connect(self._open_game)
            card.activated.connect(self._launch_game)
            self._cards.append(card)

        cols = max(1, (self._scroll.viewport().width() - 16) // (CARD_W + 16))
        row = col = 0
        for card in self._cards:
            self._grid.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

        self._empty_label.setVisible(len(self._cards) == 0)
        self._scroll.setVisible(len(self._cards) > 0)
        self._load_card_art()

    def _filtered_games(self) -> list[Game]:
        src = self._sidebar._current_source
        text = self._sidebar._search_text
        out = []
        for g in self._games:
            if src is not None and g.source != src:
                continue
            if text and text not in g.name.lower():
                continue
            out.append(g)
        out.sort(key=lambda g: (g.sort_key or g.name).lower())
        return out

    def _load_card_art(self):
        from gamehub.services import art

        for card in self._cards:
            card.set_art(art.load_grid(card.game, allow_network=False))

    def _on_filter_changed(self, _src):
        self._rebuild_cards()

    def _on_search_changed(self, _text):
        self._rebuild_cards()

    # -- navigation ----------------------------------------------------

    def _show_home(self):
        self._content.setCurrentWidget(self._home)
        self._title_label.setText("Library")
        self._back_btn.setEnabled(False)

    def _open_game(self, game: Game):
        self._gamepage.set_game(game)
        self._content.setCurrentWidget(self._gamepage)
        self._title_label.setText(game.name.replace("/", " / "))
        self._back_btn.setEnabled(True)
        self._load_hero_async(game)

    def _load_hero_async(self, game: Game):
        if game in self._hero_done:
            return
        self._hero_done.add(game)
        self._hero_signals = HeroSignals(self)
        self._hero_signals.ready.connect(self._on_hero_ready)
        threading.Thread(
            target=_hero_job,
            args=(game, self._hero_signals, self._hero_stop),
            daemon=True,
        ).start()

    def _on_hero_ready(self, payload):
        game, data = payload
        pix = bytes_to_pixmap(data)
        if pix is None:
            return
        if self._gamepage.game == game:
            self._gamepage.set_hero(pix)

    def _launch_game(self, game: Game):
        try:
            launch(game)
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Failed to launch {game.name}:\n{e}")

    def _update_proton(self):
        self._status_show("Updating Proton...")
        self._proton_worker = ProtonUpdateWorker()
        self._proton_worker.message.connect(self._status_show)
        self._proton_worker.done.connect(self._on_proton_updated)
        self._proton_worker.start()

    def _on_proton_updated(self, ok: bool, error: str):
        if ok:
            self._status_show("Proton updated")
        else:
            self._status_show("Proton update failed")
            QMessageBox.warning(self, "Proton Update Failed", error)

    def _status_show(self, text: str):
        self.statusBar().showMessage(text, 5000)

    # -- controller ----------------------------------------------------

    def closeEvent(self, event):
        self._shutdown_threads()
        super().closeEvent(event)

    def _shutdown_threads(self):
        self._controller.stop()
        self._controller.wait(2000)
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            worker.wait(3000)
        self._art_stop.set()
        self._hero_stop.set()

    def _wire_controller(self):
        self._controller.connected.connect(self._on_controller_connected)
        self._controller.button.connect(self._on_controller_button)
        self._controller.nav.connect(self._on_controller_nav)
        self._controller.start()

    def _on_controller_connected(self, connected: bool):
        self._controller_hint.setText("Gamepad" if connected else "")
        if connected:
            self._update_controller_hint()

    def _on_controller_button(self, name: str, pressed: bool):
        if not pressed:
            return
        page = self._content.currentWidget()
        if name == "a":
            self._controller_activate()
        elif name == "b":
            self._show_home()
        elif name == "start":
            if page is self._home and self._cards:
                self._launch_game(self._cards[self._card_index].game)

    def _on_controller_nav(self, direction: str, pressed: bool):
        if not pressed:
            return
        if direction == "left":
            if self._content.currentWidget() is self._gamepage:
                self._show_home()
            else:
                self._focus_card(self._card_index - 1)
        elif direction == "right":
            self._focus_card(self._card_index + 1)
        elif direction == "up":
            cols = self._grid.columnCount()
            if cols > 0:
                self._focus_card(self._card_index - cols)
        elif direction == "down":
            cols = self._grid.columnCount()
            if cols > 0:
                self._focus_card(self._card_index + cols)

    def _focus_card(self, index: int):
        if not self._cards:
            return
        index = max(0, min(len(self._cards) - 1, index))
        for i, card in enumerate(self._cards):
            card.set_focused(i == index)
        self._card_index = index
        self._scroll.ensureWidgetVisible(self._cards[index], 40, 40)
        self._update_controller_hint()

    def _controller_activate(self):
        page = self._content.currentWidget()
        if page is self._home:
            if self._cards:
                self._open_game(self._cards[self._card_index].game)
        elif page is self._gamepage:
            self._launch_game(self._gamepage.game)

    def _update_controller_hint(self):
        if not self._controller_hint.text():
            return
        page = self._content.currentWidget()
        if page is self._home:
            self._controller_hint.setText("Gamepad · A: Open  X: Launch  B: Home")
        else:
            self._controller_hint.setText("Gamepad · A: Play  B: Back")
