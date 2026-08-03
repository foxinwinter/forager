# Steam Web API usage

## Current usage

forager currently uses **no keyed Steam Web API** calls:

- Public profile XML (`https://steamcommunity.com/profiles/<steamid>/?xml=1`)
  is used to resolve a persona name from a SteamID
  (`providers/steam/account.py:account_name_from_steamid`) — no key required.
- Store search (`https://store.steampowered.com/api/storesearch/`) is used to
  resolve App IDs by name (`providers/steam/appid.py`) — no key required.
- Local art comes from the Steam client's `appcache/librarycache` and the
  Steam CDN (keyless).

## Planned usage (roadmap)

For the owned-library feature (`providers/steam/library.py`) the following
endpoints are the natural fit:

- `ISteamUser/GetPlayerSummaries` — resolve the signed-in SteamID to a persona.
- `ISteamApps/GetOwnedGames` (`steamid`, `include_appinfo=true`,
  `include_played_free_games=true`) — the full owned list with appinfo, merged
  into the local library.

For achievements (`providers/steam/achievements.py`):

- `ISteamUserStats/GetPlayerAchievements` — requires a public profile;
  otherwise fall back to the local
  `userdata/<steamid>/<appid>/achievements.vdf`.

## Design notes

- Endpoints require an API key, so the *keyless* paths above stay preferred
  where possible.
- The Steam session already exists (`providers/steam/account.py`); no
  additional auth flow should be introduced.
- All calls run off the GUI thread (`ui/workers.py` pattern) and must degrade
  to a graceful offline state (the library already renders without art).
