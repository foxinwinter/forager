from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

GAMES_DIR = Path("/nyaa/games")

GENERIC_CONTAINERS = {
    "standalone", "series", "minecraft", "steam", "rpgmaker", "rpg",
    "games", "instances", "launcher", "single", "flash",
}


class Source(Enum):
    STEAM = auto()
    MINECRAFT = auto()
    STANDALONE = auto()


@dataclass
class Game:
    name: str
    source: Source
    path: Path
    app_id: str | None = None
    launch_cmd: list[str] | None = None
    sort_key: str | None = None
    search_names: list[str] | None = None

    def __hash__(self):
        return hash((self.source, self.app_id or str(self.path)))

    def __eq__(self, other):
        if not isinstance(other, Game):
            return NotImplemented
        return (self.source, self.app_id or str(self.path)) == (
            other.source,
            other.app_id or str(other.path),
        )

    @property
    def source_name(self) -> str:
        return {
            Source.STEAM: "Steam",
            Source.MINECRAFT: "Minecraft",
            Source.STANDALONE: "Standalone",
        }[self.source]

    @property
    def sgdb_search(self) -> tuple[list[str], str] | None:
        """SGDB search plan: (queries, match_term), or None to skip search.

        Searches the holding (series) folder rather than the leaf folder name,
        so e.g. ``series/sequel/asylum`` searches ``sequel``. Returns None for
        generic container folders (minecraft, standalone, ...) to avoid wrong
        matches. ``search_names`` always wins when set.
        """
        if self.search_names:
            return (list(self.search_names), self.name)
        if self.source == Source.STEAM:
            return None
        try:
            parts = self.path.resolve().relative_to(GAMES_DIR).parts
        except ValueError:
            return None
        parts = list(parts)
        while len(parts) >= 2 and parts[-2].lower() in GENERIC_CONTAINERS:
            parts.pop()
        if len(parts) >= 2:
            return ([parts[-2]], parts[-1])
        return None
