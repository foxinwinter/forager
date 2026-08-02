from __future__ import annotations
import os
import subprocess
from pathlib import Path
from forager.core.game import Game, Source


def launch(game: Game) -> subprocess.Popen | None:
    """Launch the game and return the spawned process, or None.

    Steam's ``steam://rungameid`` command returns immediately, so the Popen
    can't be used to track the actual game — callers should treat Steam
    launches as untrackable.
    """
    match game.source:
        case Source.STEAM:
            return _launch_steam(game)

        case Source.MINECRAFT:
            return _launch_minecraft(game)

        case Source.STANDALONE:
            return _launch_standalone(game)


def _launch_steam(game: Game) -> subprocess.Popen:
    return subprocess.Popen(
        ["steam", f"steam://rungameid/{game.app_id}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _launch_minecraft(game: Game) -> subprocess.Popen:
    return subprocess.Popen(
        ["prismlauncher", "-l", game.name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _launch_standalone(game: Game) -> subprocess.Popen | None:
    exe = _find_executable(game.path)
    if not exe:
        return None
    if exe.suffix == ".exe":
        from forager.library import proton

        return proton.launch_exe(game.path, exe)
    return subprocess.Popen([str(exe)], cwd=game.path)


def _find_executable(path: Path) -> Path | None:
    if path.is_file() and os.access(path, os.X_OK):
        return path
    for pattern in ("*.x86_64", "*.sh", "*.py", "*.exe"):
        for f in sorted(path.glob(pattern)):
            return f
    return None
