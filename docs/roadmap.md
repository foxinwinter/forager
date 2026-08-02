# forager Roadmap

Everything on this list must be in place before forager is tagged `v1.0.0`
("stable"). Until then the project stays on the `0.x` line, where the public
API and features may change at any time.

| Feature | Status | Notes |
|---------|--------|-------|
| Full Steam library (all owned, not just installed) | Planned | Steam Web API / `appinfo` + the existing Steam login |
| Downloading Steam games | Planned | DepotDownloader (vendored for Steam login; steamcmd now installs Proton) + stored credentials |
| Buying Steam games | Planned | `QWebEngineView` wrapper of the real Steam store, recolored with an injected stylesheet to match the app theme (same approach as Steam's own embedded client) |
| Torrenting | Planned | `libtorrent` integration as a generic downloader; legality of torrented content is the user's responsibility |
| Steam achievements (view/display) | Planned | Local `userdata/<steamid>/<appid>/achievements.vdf` (offline, no key) and/or the Web API `ISteamUserStats/GetPlayerAchievements` |
| Epic Games support | Planned | Legendary (open-source EGS CLI) as backend: auth, download, launch |
| GOG support | Planned | GOG's unofficial web API for owned offline installers |

## Build order

1. Steam account (done: QR + username/password sign-in, persistent refresh-token session)
2. Full Steam library
3. Downloading Steam games
4. Store webview for buying
5. Epic Games
6. GOG
7. Steam achievements
8. Torrenting

The store webview requires the large `PySide6-WebEngine` dependency.
