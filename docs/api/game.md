# `Game` dataclass — reference

Source: `src/forager/core/game.py`

```python
@dataclass
class Game:
    name: str
    source: Source
    path: Path
    app_id: str | None = None
    launch_cmd: list[str] | None = None
    sort_key: str | None = None
    search_names: list[str] | None = None
```

## `Source` enum

`Source.STEAM` · `Source.MINECRAFT` · `Source.STANDALONE`

## Fields

| Field | Meaning |
|-------|---------|
| `name` | display name |
| `source` | where the game came from (drives launch + art strategy) |
| `path` | absolute folder |
| `app_id` | Steam App ID when known (Steam games always set it) |
| `launch_cmd` | explicit launch command override (optional) |
| `sort_key` | ordering key for the library grid (falls back to `name`) |
| `search_names` | authoritative names for store/search lookups |

## Properties

- `source_name` — human label (`"Steam"`, `"Minecraft"`, `"Standalone"`).
- `display_path` — path relative to the games dir starting at the holder
  folder (`drm-free/series/…`), else absolute.
- `sgdb_search` — SteamGridDB/appid search plan `(queries, match_term)` or
  `None` when searching should be skipped (Steam games, generic containers).

## Equality / hashing

`Game` is a value type keyed by `(source, app_id or path)` — equality and the
hash ignore everything else so the same game scanned twice compares equal.
