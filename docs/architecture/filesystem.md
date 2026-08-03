# Config / cache / data directory layout

Everything is derived from `core/config.py` and `core/paths.py`.

| Path | Default | Purpose |
|------|---------|---------|
| config dir | `~/.config/forager` (`FORAGER_CONFIG_DIR`) | `settings.json`, `playtime.json` |
| cache dir | `~/.cache/forager` (`FORAGER_CACHE_DIR`) | artwork caches |
| `…/art/` | — | headers, grids, heroes (`artwork/cache.py`) |
| `…/banners/` | — | game-page hero banners |
| `…/icons/` | — | tile icons |
| games dir | `~/Games` | the library (steam/, minecraft/, drm-free/) |
| steam appcache | `~/.local/share/Steam/appcache/librarycache` | Steam local art |
| `.runtime/` | under games dir | steamcmd, DepotDownloader, Proton |
| `.runtime/proton/files` | — | the shared Proton prefix |

The artwork cache helpers live in `artwork/cache.py` (with the 
game-driven dirs under the cache dir); the rest live in `core/paths.py`.

## Keyring

Credentials are not written to disk — the system keyring is used
(`keyring` Python package), service name `forager`:

- Steam username/password/login-method/steamid/`steamLoginSecure`
  (`providers/steam/account.py`);
- SteamGridDB API token (`services/steamgriddb.py`).

## Assets (read-only, packaged)

Bundled icons and the VT323 font ship in `src/forager/assets/` (icons/, fonts/)
and are resolved at runtime via `importlib.resources` in `core/paths.py` —
identical behaviour from a source checkout and an installed wheel. They are
never written to.
