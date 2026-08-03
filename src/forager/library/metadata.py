"""Library metadata helpers: search matching and sorting for the game list.

These are the pure functions behind the library page's search box and
ordering (see ``forager.ui.pages.game_grid``). Keeping them here means the
matching/ordering rules are unit-testable without a widget tree.
"""
from __future__ import annotations

from forager.core.game import Game


def matches_query(game: Game, query: str) -> bool:
    """Case-insensitive substring match of *query* against the game name.

    An empty query matches everything.
    """
    if not query:
        return True
    return query.lower() in (game.name or "").lower()


def sort_key(game: Game) -> str:
    """Lowercased ordering key for a game (title, falling back to name)."""
    return (game.sort_key or game.name or "").lower()


def filter_games(games: list[Game], query: str) -> list[Game]:
    """Filter *games* to those matching *query* (order preserved)."""
    if not query:
        return list(games)
    return [g for g in games if matches_query(g, query)]
