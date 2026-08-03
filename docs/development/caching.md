# Caching

All caches are plain files under the user cache dir
(`~/.cache/forager` by default, override with `FORAGER_CACHE_DIR`).
Directories are created lazily.

## Artwork caches (`artwork/cache.py`)

| Directory | Contents |
|-----------|----------|
| `art/` | headers, grids, heroes |
| `banners/` | game-page hero banners |
| `icons/` | tile icons |

Entries are keyed by a SHA-256 of the game identity (`app_id` or name),
truncated to 16 hex chars, written as `<key>.png`. Lookups check the cache
before any network call; network fetches re-populate the cache on success.

## App-ID cache (`providers/steam/appid.py`)

`art/steam_app_ids.json` maps normalized search terms to resolved App IDs
(empty string = known negative). This makes store searches one-shot per term.

## Playtime (`library/playtime.py`)

`playtime.json` sits next to `settings.json` (config dir, *not* the cache dir)
because it is user state, not a rebuildable cache. See
[architecture/filesystem.md](../architecture/filesystem.md).

## Cache invalidation

- Art caches are never invalidated on purpose; a missing/stale file simply
  falls through to the next resolution step.
- The app-id cache can be cleared by deleting `art/steam_app_ids.json`.
- Nothing is written when a fetch fails, so transient network errors never
  poison the cache.
