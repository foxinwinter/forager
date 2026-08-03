"""Steam achievements (roadmap item 7).

Planned: local ``userdata/<steamid>/<appid>/achievements.vdf`` (offline, no
API key) and/or the Web API ``ISteamUserStats/GetPlayerAchievements``. See
``docs/providers/steam.md``.

Nothing is implemented yet.
"""
from __future__ import annotations


def player_achievements(steamid: str, app_id: str) -> list[dict]:
    """Return earned achievements for a player/app (placeholder).

    Raises ``NotImplementedError`` until achievements land (roadmap item 7).
    """
    raise NotImplementedError("Steam achievements are planned (roadmap item 7)")
