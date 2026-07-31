from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from gamehub.ui.theme import apply as apply_theme
from gamehub.ui.main_window import MainWindow


class ForagerApp(QApplication):
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName("forager")
        self.setOrganizationName("forager")

        apply_theme(self)

        self._window = MainWindow()
        self._window.show()
