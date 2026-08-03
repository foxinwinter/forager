# Settings lifecycle & persistence

## Storage (`core/config.py`)

Settings are a single JSON document at
`~/.config/forager/settings.json` (or `$FORAGER_CONFIG_DIR`). The `Settings`
class:

- **loads** on construction: reads the file, tolerating missing/corrupt JSON,
  and deep-merges the user data over `DEFAULTS` so new keys always exist;
- **exposes** the values via properties (`games_dir`, `steam_appcache`,
  `proton_features` / `proton_feature(name)`) and generic `get`/`set`;
- **saves** the whole document on demand (`save()`).

A process-wide `settings = Settings()` singleton is created at import time and
used everywhere.

## Defaults

```json
{
  "games_dir": "~/Games",
  "steam_appcache": "~/.local/share/Steam/appcache/librarycache",
  "display_size": "medium",
  "proton": { "features": { "rpgmaker_vxace_rtp": false } }
}
```

## Edit flow (UI)

The **Settings…** dialog (`ui/dialogs/settings.py`) is the only writer:

1. `LibraryTab` edits `games_dir`, `steam_appcache`, `display_size`;
   `ProtonTab` edits the Proton feature set and triggers
   `update_proton_requested`; `AccountTab` manages Steam + SteamGridDB.
2. On **Save**, the main window reads the dialog's accessors
   (`games_dir_text()`, `selected_card_size()`, `feature_values()`) and
   persists them, then re-scans if the games dir changed
   (`games_dir_changed` signal) or refreshes the grid.

## Runtime locations derived from settings

- `games_dir` drives the scanner (`core/paths.py:games_dir`).
- `steam_appcache` drives local Steam art lookups.
- `display_size` drives the grid card size (`resolve_card_size` in
  `ui/dialogs/settings.py`).
- Proton features are consulted by `compatibility/proton.py`.
