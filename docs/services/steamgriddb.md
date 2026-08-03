# SteamGridDB integration

Source: `src/forager/services/steamgriddb.py`

## What it does

A small client for the **SteamGridDB API v2** (`https://www.steamgriddb.com/api/v2`)
used by the artwork pipeline when no local art or Steam CDN art exists:

- **grids / headers / banners** — `fetch_grid_bytes_for_steam`,
  `fetch_header_bytes_for_steam`, `fetch_banner_bytes_for_steam` (by app id),
  plus `fetch_*_for_game` (by search).
- **icons** — `fetch_icon_bytes_for_steam` / `fetch_icon_bytes_for_game`.

The resolution order that consumes these is documented in
[architecture/artwork.md](../architecture/artwork.md).

## Authentication

SteamGridDB requests are keyed by an API token:

- stored in the system keyring (service `forager`, user `steamgriddb`) via
  `set_api_key`;
- read by `get_api_key`, falling back to the `STEAMGRIDDB_API_KEY`
  environment variable;
- the token is obtained on the SteamGridDB site (profile → preferences → API)
  and entered through the Settings → Account tab
  (`ui/dialogs/steamgriddb_dialog.py`).

## Policy

A failed/absent token simply means art falls through to the next resolution
step (generated placeholders); SteamGridDB errors are non-fatal.
