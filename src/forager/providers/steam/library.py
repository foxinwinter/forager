"""Owned Steam library retrieval (roadmap item 2).

Planned: the Steam Web API (``ISteamApps/GetOwnedGames`` / ``appinfo``) driven
by the existing Steam session from ``forager.providers.steam.account``, merged
into the local library so all *owned* titles are listed, not just installed
ones. See ``docs/providers/steam.md``.

Nothing is implemented yet; the entry point below is a placeholder so the
interface is discoverable.
"""
from __future__ import annotations


def owned_games(steamid: str) -> list[dict]:
    """Return the owned games for *steamid* (placeholder).

    Raises ``NotImplementedError`` until the Steam Web API integration lands.
    """
    raise NotImplementedError("owned Steam library retrieval is planned (roadmap item 2)")
