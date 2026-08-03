# Artwork pipeline API — reference

Source: `src/forager/artwork/pipeline.py`

## Pixmap loaders (used by the UI)

```python
load_header(game, allow_network=True) -> QPixmap | None   # wide header art
load_grid(game,   allow_network=True) -> QPixmap | None   # portrait grid art
load_hero(game,   allow_network=True) -> QPixmap | None   # game-page hero
load_logo(game) -> QPixmap | None                         # logo (appcache/CDN)
```

## Byte loaders (used by background workers)

```python
load_header_bytes(game, allow_network=True) -> bytes | None
load_grid_bytes(game,   allow_network=True) -> bytes | None
load_hero_bytes(game,   allow_network=True) -> bytes | None
```

`allow_network=False` restricts the resolution to local sources (appcache +
disk cache) — used by the grid to avoid network storms.

## Resolution order (per image)

local Steam appcache → on-disk art cache → Steam CDN (resolved app_id) →
SteamGridDB by app id → SteamGridDB by search → generated placeholder.

## Supporting modules

- `artwork/placeholder.py` — `placeholder_card(game, w, h)`,
  `placeholder_grid(game, w, h)`, `register_placeholder_font()`.
- `artwork/pixmap_utils.py` — `bytes_to_pixmap`, `scale_crop`, `scaled`.
- `services/icon_provider.py` — `load_icon(game, allow_network=True)` /
  `load_icon_bytes(game, allow_network=True)` (tile icons).
- `providers/steam/appid.py` — `steam_app_id(game) -> str | None`.
- `artwork/cache.py` — cache directory helpers.

See [architecture/artwork.md](../architecture/artwork.md).
