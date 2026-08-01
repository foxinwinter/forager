from __future__ import annotations
import atexit
import threading
from shiboken6 import isValid
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox,
    QStackedWidget, QApplication,
)

from forager.core.game import Game
from forager.core.config import settings
from forager.library.launcher import launch
from forager.core.controller import ControllerPoller
from forager.services.pixmap_utils import bytes_to_pixmap
from forager.ui.theme import C
from forager.ui.widgets.sidebar import Sidebar
from forager.ui.widgets.titlebar import TitleBar
from forager.ui.pages.game_grid import GameGrid
from forager.ui.pages.gamepage import GamePage
from forager.ui.dialogs.settings import SettingsDialog, resolve_card_size
from forager.ui.pages.downloads import DownloadsPage
from forager.ui.widgets.controller_nav import GamepadNavigation
from forager.ui.workers import (
    ScanWorker, ProtonUpdateWorker, TestDownloadWorker,
    ToolUpdateWorker,
    ArtSignals, HeroSignals, _art_job, _hero_job,
    ToolUpdateSignals, _tool_update_check_job,
)

_WORKER_ATTRS = (
    "_worker", "_test_worker", "_update_runner", "_proton_worker",
)

_orphaned_workers: set = set()


def _orphan_worker(worker: QThread) -> None:
    """Detach a worker so it can finish on its own without crashing at exit.

    A QThread must never be destroyed while its thread is still running (Qt
    warns and aborts). Workers doing blocking network I/O can't always be
    stopped synchronously, so keep them alive until ``finished`` instead of
    letting the window teardown destroy them mid-run.
    """
    if worker in _orphaned_workers:
        return
    if not isValid(worker):
        return
    worker.setParent(None)
    _orphaned_workers.add(worker)
    worker.finished.connect(lambda: _orphaned_workers.discard(worker))


def _drain_orphans() -> None:
    """Wait for detached workers at process exit so their QThread objects are
    never destroyed while still running (Qt aborts on that)."""
    for worker in list(_orphaned_workers):
        if isValid(worker) and worker.isRunning():
            worker.wait(35000)


atexit.register(_drain_orphans)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._games: list[Game] = []
        self._card_w, self._card_h = resolve_card_size(settings.get("display_size", "medium"))
        self._controller = ControllerPoller(self)
        self._closed = False
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
        QTimer.singleShot(100, self._check_tool_updates)
    # -- UI ------------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle("forager")
        self.setMinimumSize(760, 480)
        self.resize(1100, 700)

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

        self._titlebar = TitleBar()
        self._titlebar.settings_requested.connect(self._open_settings)
        self._titlebar.update_proton_requested.connect(self._update_proton)
        self._titlebar.test_download_requested.connect(self._test_download)
        self._titlebar.back_requested.connect(self._show_home)
        right_layout.addWidget(self._titlebar)

        self._content = QStackedWidget()
        right_layout.addWidget(self._content, stretch=1)
        layout.addWidget(right, stretch=1)

        self._sidebar = Sidebar()
        layout.addWidget(self._sidebar)

        self._home = self._build_home()
        self._content.addWidget(self._home)

        self._gamepage = GamePage()
        self._content.addWidget(self._gamepage)

        self._downloads_page = DownloadsPage()
        self._content.addWidget(self._downloads_page)

        self._sidebar.game_selected.connect(self._open_game)
        self._sidebar.search_changed.connect(self._on_search_changed)
        self._sidebar.download_clicked.connect(self._show_downloads)
        self._downloads_page.cancel_requested.connect(self._cancel_proton_update)
        self._titlebar.run_updates_requested.connect(self._run_tool_updates)
        self._gamepage.play.connect(self._launch_game)
        self._gamepage.back_requested.connect(self._show_home)

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

        self._grid = GameGrid(self._card_w, self._card_h)
        self._grid.card_clicked.connect(self._open_game)
        self._grid.card_activated.connect(self._launch_game)
        v.addWidget(self._grid, stretch=1)

        return page

    def _open_settings(self):
        self._games_dir_before = str(settings.games_dir)
        dialog = SettingsDialog(self)
        dialog.update_proton_requested.connect(self._update_proton)
        dialog.games_dir_changed.connect(self._reload_library)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            size_key = dialog.selected_card_size()
            w, h = resolve_card_size(size_key)
            if (w, h) != (self._card_w, self._card_h):
                self._card_w, self._card_h = w, h
                self._grid.set_card_size(w, h)
            if dialog.games_dir_text() != str(self._games_dir_before):
                self._reload_library()
            else:
                self._status_show("Settings saved")

    def _reload_library(self):
        self._status_show("Rescanning library…")
        self._art_stop.set()
        self._hero_stop.set()
        self._hero_done.clear()
        self._load_games()

    # -- game loading --------------------------------------------------

    def _load_games(self):
        if getattr(self, "_closed", False):
            return
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
        self._grid.set_games(self._games)
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
        self._grid.set_card_art(game, pix)

    def _on_icon_ready(self, payload):
        game, data = payload
        pix = bytes_to_pixmap(data)
        if pix is None:
            return
        self._sidebar.set_icon(game, QIcon(pix))

    def _on_search_changed(self, text):
        self._grid.set_search(text)

    # -- navigation ----------------------------------------------------

    def _show_home(self):
        self._content.setCurrentWidget(self._home)
        self._titlebar.set_back_enabled(False)

    def _show_downloads(self):
        self._content.setCurrentWidget(self._downloads_page)
        self._titlebar.set_back_enabled(True)

    def _open_game(self, game: Game):
        self._gamepage.set_game(game)
        self._content.setCurrentWidget(self._gamepage)
        self._titlebar.set_back_enabled(True)
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
        self._proton_cancel = threading.Event()
        self._status_show("Updating Proton...")
        self._sidebar.begin_download("Proton Experimental")
        self._downloads_page.begin("Proton Experimental")
        self._proton_worker = ProtonUpdateWorker(self._proton_cancel, self)
        self._proton_worker.message.connect(self._status_show)
        self._proton_worker.message.connect(self._status_show)
        self._proton_worker.progress.connect(self._on_download_progress)
        self._proton_worker.done.connect(self._on_proton_updated)
        self._proton_worker.start()

    def _test_download(self):
        self._sidebar.begin_download("Test Download")
        self._downloads_page.begin("Test Download")
        self._test_worker = TestDownloadWorker(self)
        self._test_worker.progress.connect(self._on_download_progress)
        self._test_worker.done.connect(self._on_test_downloaded)
        self._test_worker.start()

    def _on_test_downloaded(self, ok: bool, result: str):
        self._sidebar.hide_download()
        if ok:
            self._status_show("Test download complete")
            self._downloads_page.complete(result)
        else:
            self._status_show("Test download cancelled")
            self._downloads_page.cancelled()

    def _cancel_proton_update(self):
        cancel = getattr(self, "_proton_cancel", None)
        if cancel is not None:
            cancel.set()

    def _on_download_progress(self, progress):
        self._sidebar.set_download_progress(progress)
        self._downloads_page.set_progress(progress)

    def _on_proton_updated(self, ok: bool, result: str):
        self._sidebar.hide_download()
        if ok:
            self._status_show("Proton updated")
            self._downloads_page.complete(result)
        elif result == "Download cancelled":
            self._status_show("Proton update cancelled")
            self._downloads_page.cancelled()
        else:
            self._status_show("Proton update failed")
            self._downloads_page.failed(result)
            QMessageBox.warning(self, "Proton Update Failed", result)

    def _status_show(self, text: str):
        self.statusBar().showMessage(text, 5000)

    # -- tool updates ------------------------------------------------

    def _check_tool_updates(self):
        if getattr(self, "_closed", False):
            return
        self._tool_updates: list = []
        self._tool_check_signals = ToolUpdateSignals(self)
        self._tool_check_signals.done.connect(self._on_tool_check_done)
        self._tool_check_stop = threading.Event()
        threading.Thread(
            target=_tool_update_check_job,
            args=(self._tool_check_signals, self._tool_check_stop),
            daemon=True,
        ).start()

    def _on_tool_check_done(self, updates: list):
        self._tool_updates = updates
        self._titlebar.set_updates([u.name for u in updates])

    def _run_tool_updates(self):
        updates = getattr(self, "_tool_updates", [])
        if not updates:
            return
        names = ", ".join(u.name for u in updates)
        reply = QMessageBox.question(
            self, "Tool Updates",
            f"Update {names} to the latest version?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._status_show("Updating tools...")
        self._update_runner = ToolUpdateWorker(self)
        self._update_runner.done.connect(self._on_tool_update_done)
        self._update_runner.start()

    def _on_tool_update_done(self, ok: bool, result: str):
        if ok:
            self._titlebar.set_updates([])
            self._status_show(result)
        else:
            self._status_show(f"Tool update failed: {result}")

    # -- controller ----------------------------------------------------

    def closeEvent(self, event):
        self._closed = True
        self._shutdown_threads()
        super().closeEvent(event)

    def _shutdown_threads(self):
        self._nav.shutdown()
        cancel = getattr(self, "_proton_cancel", None)
        if cancel is not None:
            cancel.set()
        stop = getattr(self, "_tool_check_stop", None)
        if stop is not None:
            stop.set()
        for name in _WORKER_ATTRS:
            worker = getattr(self, name, None)
            if worker is None or not isValid(worker):
                continue
            if worker.isRunning():
                worker.requestInterruption()
                if not worker.wait(3000):
                    _orphan_worker(worker)
        self._art_stop.set()
        self._hero_stop.set()

    def _wire_controller(self):
        self._nav = GamepadNavigation(
            self._controller,
            is_on_home=lambda: self._content.currentWidget() is self._home,
            is_on_gamepage=lambda: self._content.currentWidget() is self._gamepage,
            focused_game=lambda: self._grid.game_at(self._grid.current_index()),
            gamepage_game=lambda: self._gamepage.game,
            open_game=self._open_game,
            launch_game=self._launch_game,
            show_home=self._show_home,
            move_focus=self._move_focus,
            column_count=self._grid.column_count,
            set_hint=self._titlebar.set_controller_hint,
        )

    def _move_focus(self, delta: int):
        self._grid.focus_index(self._grid.current_index() + delta)
