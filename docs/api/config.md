# Settings API — reference

Source: `src/forager/core/config.py`

## Module-level

- `DEFAULTS` — the default settings document.
- `settings` — the process-wide `Settings` singleton (import and use).
- `default_config_dir()` — config dir (env `FORAGER_CONFIG_DIR`, else
  `~/.config/forager`).
- `default_cache_dir()` — cache dir (env `FORAGER_CACHE_DIR`, else
  `~/.cache/forager`).

## `Settings`

```python
settings = Settings(path=None)          # path default: ~/.config/forager/settings.json
settings.load()                         # read + deep-merge over DEFAULTS (idempotent)
settings.save()                         # write JSON back (creates parents)
settings.get(key, default=None)         # raw access into the merged document
settings.set(key, value)                # raw write into the merged document
settings.games_dir -> Path              # ~/Games by default
settings.steam_appcache -> Path         # Steam librarycache folder
settings.proton_features -> dict        # {"rpgmaker_vxace_rtp": bool}
settings.proton_feature(name) -> bool   # enabled flag for a named feature
settings.data -> dict                   # the merged document
```

Loads tolerate missing or corrupt JSON (fall back to defaults); `save()`
writes the whole merged document.

## Related

- Filesystem locations derived from settings: `forager.core.paths` and
  `forager.artwork.cache`.
- The Settings dialog (`ui/dialogs/settings.py`) is the UI writer.
- [architecture/settings.md](../architecture/settings.md) describes the
  lifecycle.
