# Artwork generation & cache pipeline

```
artwork/pipeline.py
  load_header / load_grid / load_hero / load_logo  (QPixmap)
  load_header_bytes / load_grid_bytes / load_hero_bytes  (bytes)
        resolution order per image:
          1. local Steam appcache art            (steam_appcache_dir, Source.STEAM)
          2. on-disk art cache                   (artwork/cache.py dirs)
          3. Steam CDN for resolved app_id       (appid resolution)
          4. SteamGridDB by app id               (services/steamgriddb.py)
          5. SteamGridDB by search               (services/steamgriddb.py)
          6. generated placeholder               (artwork/placeholder.py)
```

## Pipeline (`artwork/pipeline.py`)

All entry points resolve to a `QPixmap` (or raw `bytes`) following the strict
resolution order above. The app_id for non-Steam games is resolved by
`providers/steam/appid.py` (confident store-title matches only, cached on disk
per search term — see [development/caching.md](../development/caching.md)).

## Icons (`services/icon_provider.py`)

`load_icon_bytes` / `load_icon` fetch tile icons, preferring the Steam
`librarycache` directory, then SteamGridDB (via `services/steamgriddb.py`),
then the local `.exe` PE icons (`artwork/pe_icons.py`). Icons are cached in the
icons cache dir.

## Placeholders (`artwork/placeholder.py`)

When no art exists at all, `placeholder_card` renders the sunburst banner used
on the game page and `placeholder_grid` the glow cover used for grid tiles.
Both draw the game's local icon with a soft shadow and the game name in the
bundled VT323 font.

## Cache (`artwork/cache.py`)

Cache directories live under the user cache dir (`~/.cache/forager` by
default): `art/` (headers/grids/heroes), `banners/` and `icons/`. See
[architecture/filesystem.md](filesystem.md) and
[development/caching.md](../development/caching.md).
