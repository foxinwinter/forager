# Provider abstraction

```
providers/
  steam/
    account.py        stored credentials + session verification (DepotDownloader)
    auth.py           QR / device-code Steam authentication flow
    appid.py          Steam App ID resolution by name (confident store matches)
    library.py        owned-library retrieval   (planned — roadmap item 2)
    downloader.py     Steam game downloads      (planned — roadmap item 3)
    achievements.py   Steam achievements        (planned — roadmap item 7)
  epic/               placeholder (planned — Legendary backend)
  gog/                placeholder (planned — unofficial web API)
  torrent/            placeholder (planned — libtorrent generic downloader)
```

## The idea

Every store/provider contributes a uniform surface so the rest of the app
(library grid, game page, downloads page, launcher) does not care *which*
store a game came from:

- **ownership** → games that exist on the provider for the signed-in account;
- **download** → pull a game's files with progress (driving the existing
  downloads page);
- **launch** → reuse `library/launcher.py`.

## Current state

Only Steam is implemented, and only partially: account/auth/appid are real;
`library.py`, `downloader.py` and `achievements.py` are honest placeholders
that raise `NotImplementedError` with pointers to the roadmap. The epic/gog/
torrent packages are empty packages with design-note docs under
`docs/providers/`.

## Services layer

`services/` is the thin HTTP/online layer used *by* the artwork pipeline
rather than a store abstraction:

- `steamgriddb.py` — SteamGridDB API v2 client (token stored in keyring).
- `icon_provider.py` — icon fetching and caching on top of the Steam appcache
  and SteamGridDB.
