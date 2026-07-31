from __future__ import annotations
import os
import subprocess
from pathlib import Path
from forager.core.game import Game, Source


def launch(game: Game) -> None:
    match game.source:
        case Source.STEAM:
            _launch_steam(game)

        case Source.MINECRAFT:
            _launch_minecraft(game)

        case Source.STANDALONE:
            _launch_standalone(game)


def _launch_steam(game: Game) -> None:
    subprocess.Popen(
        ["steam", f"steam://rungameid/{game.app_id}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _launch_minecraft(game: Game) -> None:
    subprocess.Popen(
        ["prismlauncher", "-l", game.name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _launch_standalone(game: Game) -> None:
    exe = _find_executable(game.path)
    if not exe:
        return
    if exe.suffix == ".exe":
        from forager.library import proton

        proton.launch_exe(game.path, exe)
    else:
        subprocess.Popen([str(exe)], cwd=game.path)


def _find_executable(path: Path) -> Path | None:
    if path.is_file() and os.access(path, os.X_OK):
        return path
    for pattern in ("*.x86_64", "*.sh", "*.py", "*.exe"):
        for f in sorted(path.glob(pattern)):
            return f
    return None
