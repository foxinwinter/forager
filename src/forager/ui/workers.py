"""Background QThreads and job functions for scanning and art fetching.

Network / disk work never runs on the GUI thread; these workers emit results
back through Qt signals. Each exposes a stop ``threading.Event`` so the
window can cancel cleanly on shutdown.
"""
from __future__ import annotations
import threading
from PySide6.QtCore import QThread, QObject, Signal

from forager.core.game import Game
from forager.library.scanner import scan_all


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
        from forager.library.proton import update_proton

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
    from forager.services import art
    from forager.library.icon_provider import load_icon_bytes

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
    from forager.services import art

    if stop_event.is_set():
        return
    data = art.load_hero_bytes(game)
    if data:
        signals.ready.emit((game, data))
