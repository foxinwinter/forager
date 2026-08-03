# Testing

## Running the suite

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest -q
```

- `QT_QPA_PLATFORM=offscreen` (also forced in `tests/conftest.py`) lets every
  Qt-dependent test run without a display server or Wayland session.
- `PYTHONPATH=src` puts the package on the path without installing.

## Test model

- Plain `pytest`, no plugins beyond Qt's offscreen platform.
- Tests that touch network paths monkeypatch the network callables (e.g.
  `appid._steam_store_search`) so the suite is deterministic and offline.
- Cache-dependent code uses `tmp_path` + monkeypatched path/module globals
  (`_isolated_cache` fixture in `tests/test_art_steam.py`) to keep tests
  isolated from the real `~/.cache` and from each other.
- QPixmap-returning helpers are exercised headlessly (offscreen platform
  renders fine for pixel-independent assertions).

## Coverage of the suite

| Test file | Covers |
|-----------|--------|
| `test_scanner.py` | library discovery from a temp games dir |
| `test_game.py` | `Game` parsing / desktop files |
| `test_launcher.py` | launch strategy dispatch (monkeypatches Proton) |
| `test_steam.py` | `providers/steam/account` (fake keyring) |
| `test_steam_auth.py` | `providers/steam/auth` QR/device flow |
| `test_art_placeholder.py` | placeholder art rendering |
| `test_art_steam.py` | appid resolution + art pipeline resolution order |
| `test_icons.py` | bundled icons load and recolor |
| `test_tool_updates.py` | bundled-tool update detection |

## Writing new tests

Mirror the module name, keep network off, and prefer behavioural assertions
over internal-pixel checks. UI behaviour can be asserted via widget state and
signal emission rather than screenshot comparisons.
