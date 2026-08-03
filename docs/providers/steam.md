# Steam provider

Source: `src/forager/providers/steam/`

## Implemented

### `account.py` — account & session management

- Credentials live in the system keyring (service `forager`): username,
  password, login method, steamid and `steamLoginSecure`.
- `set_credentials` / `set_web_username` / `set_steam_session` store sessions;
  `get_*` accessors read them; `clear_credentials` / `clear_session` drop them.
- `verify_login` validates a username/password against Steam by running a
  manifest-only DepotDownloader depot fetch, handling Steam Guard prompts via a
  callback and a 180 s timeout.
- `verify_session` reuses a stored refresh token (no password/guard).
- `steamid_from_cookie` parses a `steamLoginSecure` cookie;
  `account_name_from_steamid` resolves a persona name from the public profile
  XML (no key required).

### `auth.py` — QR / device authentication

Implements Steam's `IAuthenticationService` flow (QR poll + finalize,
email-code guard for new devices). `SteamAuthError` and the email-code marker
`GUARD_EMAIL_CODE` are consumed by `ui/dialogs/steam_auth_dialog.py`.

### `appid.py` — App ID resolution by name

For games not installed through Steam, guesses the Steam App ID from a
confident store-title search (exact or distinctive-prefix matches only).
Results cache to `art/steam_app_ids.json` in the cache dir, keyed per search
term. Used by the art pipeline so CDN art can be fetched for non-Steam games.

## Planned (roadmap)

- `library.py` — owned library via the Steam Web API (`ISteamApps/GetOwnedGames`
  / `appinfo`), merged into the local library so *all* owned titles are listed.
  See [docs/services/steam_web_api.md](../services/steam_web_api.md).
- `downloader.py` — DepotDownloader-driven game downloads driving the
  downloads page; account.py already vendors DepotDownloader for login, and
  `compatibility/proton.py` reuses it for Proton installs.
- `achievements.py` — local `userdata/<steamid>/<appid>/achievements.vdf`
  (offline) and/or `ISteamUserStats/GetPlayerAchievements`.
