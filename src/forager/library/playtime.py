"""Per-game playtime tracking.

Sessions are recorded for games launched through forager. A session keeps
accumulating while the spawned child process is still alive; ``last_played``
is stamped at launch time, so the Recently Played row works even for Steam
games (the ``steam://rungameid`` command exits immediately, so Steam playtime
is not accumulated — only the last-played stamp). State persists to
``playtime.json`` next to ``settings.json``.
"""
from __future__ import annotations
import json
import subprocess
import time
from pathlib import Path

from forager.core.game import Game
from forager.utils.paths import playtime_file


def game_key(game: Game) -> str:
    """Stable identity for a game across scans.

    Steam games key on the app id; everything else keys on the resolved path
    (paths are unique per source, and standalone/Minecraft games have no id).
    """
    if game.app_id:
        return f"steam:{game.app_id}"
    try:
        path = str(game.path.resolve())
    except OSError:
        path = str(game.path)
    return f"{game.source.name.lower()}:{path}"


def format_playtime(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)} s"
    if seconds < 3600:
        return f"{int(seconds // 60)} min"
    return f"{seconds / 3600:.1f} h"


class PlaytimeStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else playtime_file()
        self._data: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        data: dict = {}
        try:
            if self.path.is_file():
                raw = json.loads(self.path.read_text("utf-8"))
                if isinstance(raw, dict):
                    data = raw
        except (OSError, json.JSONDecodeError):
            data = {}
        self._data = data

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2) + "\n", "utf-8")
        except OSError:
            pass

    def get(self, key: str) -> dict:
        entry = self._data.get(key)
        if entry is None or not isinstance(entry, dict):
            entry = {}
        return entry

    def playtime(self, key: str) -> float:
        return float(self.get(key).get("playtime", 0) or 0)

    def last_played(self, key: str) -> float:
        return float(self.get(key).get("last_played", 0) or 0)

    def touch(self, key: str, when: float | None = None) -> None:
        """Stamp a launch without changing accumulated playtime."""
        entry = dict(self.get(key))
        entry["last_played"] = time.time() if when is None else when
        entry["playtime"] = float(entry.get("playtime", 0) or 0)
        self._data[key] = entry

    def add(self, key: str, seconds: float) -> None:
        if seconds <= 0:
            return
        entry = dict(self.get(key))
        entry["playtime"] = float(entry.get("playtime", 0) or 0) + seconds
        entry["last_played"] = float(entry.get("last_played", 0) or 0)
        self._data[key] = entry


class PlaytimeTracker:
    """Tracks live sessions and exposes recently-played ranking.

    A session is created on launch and accumulates time on each ``tick``
    while the spawned process is alive; when it exits the final chunk is
    added and the session is dropped. ``flush`` ends every session and saves.
    """

    def __init__(self, store: PlaytimeStore | None = None):
        self._store = store if store is not None else PlaytimeStore()
        self._sessions: dict[str, dict] = {}

    @property
    def store(self) -> PlaytimeStore:
        return self._store

    def has_sessions(self) -> bool:
        return bool(self._sessions)

    def begin(self, game: Game, proc: subprocess.Popen | None) -> None:
        """Start a session. ``proc`` may be None when the game can't be
        tracked (Steam: the CLI command returns immediately)."""
        key = game_key(game)
        self._store.touch(key)
        if proc is not None:
            self._sessions[key] = {"proc": proc, "last": time.time()}
        self._store.save()

    def tick(self) -> bool:
        """Accumulate elapsed time for live sessions. Returns True when the
        store changed (so the UI can refresh)."""
        now = time.time()
        dirty = False
        for key, sess in list(self._sessions.items()):
            proc = sess["proc"]
            running = proc is not None and proc.poll() is None
            if running:
                self._store.add(key, max(0.0, now - sess["last"]))
                sess["last"] = now
                dirty = True
            else:
                if proc is not None:
                    self._store.add(key, max(0.0, now - sess["last"]))
                    dirty = True
                del self._sessions[key]
        if dirty:
            self._store.save()
        return dirty

    def flush(self) -> None:
        self.tick()
        self._sessions.clear()
        self._store.save()

    def recently_played(self, games: list[Game], limit: int = 8) -> list[Game]:
        """Games with a last-played stamp, newest first."""
        ranked = [
            g for g in games
            if self._store.last_played(game_key(g)) > 0
        ]
        ranked.sort(key=lambda g: self._store.last_played(game_key(g)), reverse=True)
        return ranked[:limit]
