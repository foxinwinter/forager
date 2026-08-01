"""Gamepad (evdev) navigation glue for the main window.

Turns raw controller events into window actions: A activates, B goes home,
Start launches the focused game, and the d-pad moves card focus. Page-aware
decisions are made here through injected callbacks so the main window stays
small and this stays testable.
"""
from __future__ import annotations
from typing import Callable


class GamepadNavigation:
    def __init__(
        self,
        controller,
        *,
        is_on_home: Callable[[], bool],
        is_on_gamepage: Callable[[], bool],
        focused_game: Callable[[], object],
        gamepage_game: Callable[[], object],
        open_game: Callable[[object], None],
        launch_game: Callable[[object], None],
        show_home: Callable[[], None],
        move_focus: Callable[[int], None],
        column_count: Callable[[], int],
        set_hint: Callable[[str], None],
    ):
        self._controller = controller
        self._is_on_home = is_on_home
        self._is_on_gamepage = is_on_gamepage
        self._focused_game = focused_game
        self._gamepage_game = gamepage_game
        self._open_game = open_game
        self._launch_game = launch_game
        self._show_home = show_home
        self._move_focus = move_focus
        self._column_count = column_count
        self._set_hint = set_hint
        self._connected = False

        controller.connected.connect(self._on_connected)
        controller.button.connect(self._on_button)
        controller.nav.connect(self._on_nav)
        controller.start()

    def shutdown(self):
        self._controller.stop()
        self._controller.wait(2000)

    # -- events --------------------------------------------------------

    def _on_connected(self, connected: bool):
        self._connected = connected
        self._refresh_hint()

    def _on_button(self, name: str, pressed: bool):
        if not pressed:
            return
        if name == "a":
            self._activate()
        elif name == "b":
            self._show_home()
        elif name == "start":
            if self._is_on_home():
                game = self._focused_game()
                if game is not None:
                    self._launch_game(game)

    def _on_nav(self, direction: str, pressed: bool):
        if not pressed:
            return
        if direction == "left":
            if self._is_on_gamepage():
                self._show_home()
            else:
                self._move_focus(-1)
        elif direction == "right":
            self._move_focus(+1)
        elif direction == "up":
            cols = self._column_count()
            if cols > 0:
                self._move_focus(-cols)
        elif direction == "down":
            cols = self._column_count()
            if cols > 0:
                self._move_focus(+cols)
        self._refresh_hint()

    # -- actions -------------------------------------------------------

    def _activate(self):
        if self._is_on_home():
            game = self._focused_game()
            if game is not None:
                self._open_game(game)
        elif self._is_on_gamepage():
            game = self._gamepage_game()
            if game is not None:
                self._launch_game(game)

    def _refresh_hint(self):
        if not self._connected:
            self._set_hint("")
            return
        if self._is_on_home():
            self._set_hint("Gamepad · A: Open  X: Launch  B: Home")
        else:
            self._set_hint("Gamepad · A: Play  B: Back")
