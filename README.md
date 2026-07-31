# forager

A Steam-style game launcher for your local game library.

## Features

- **Library view** — Steam-style grid of cover tiles, with a sidebar to filter
  by source (Steam / Minecraft / Standalone) and search.
- **Gamepad support** — navigate and launch with a controller (via `evdev`).
- **Cover art** — pulls portrait grid art, headers, and icons from local Steam
  files, the Steam CDN, and SteamGridDB (token stored in your system keyring).
- **Proton** — runs standalone Windows `.exe` games through a single shared
  Proton prefix. Add extras to the prefix (e.g. the RPG Maker VX Ace RTP) from
  the Settings dialog.

## Layout

Your game library folder is expected to look like:

```
~/Games/
├── steam/
│   └── steamapps/            # appmanifest_*.acf + common/<name>
├── minecraft/                # one folder per Minecraft instance
└── standalone/
    ├── <game>/               # loose games (finds *.x86_64, *.sh, *.py, *.exe)
    └── series/
        └── <series>/<game>/  # games grouped by series
```

## Install

```sh
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/gamehub
```

or use `run.sh` with an existing virtualenv:

```sh
GAMEHUB_VENV=/path/to/venv ./run.sh
```

## Configuration

Settings are stored in `~/.config/gamehub/settings.json`; cover art caches live
in `~/.cache/gamehub/`. Open the **forager → Settings…** menu to change the game
library folder, the Steam appcache/librarycache folder, the Proton prefix name,
and which extras get added to the prefix.

Environment overrides:

- `GAMEHUB_CONFIG_DIR` — config directory (default `~/.config/gamehub`)
- `GAMEHUB_CACHE_DIR` — cache directory (default `~/.cache/gamehub`)
- `STEAMGRIDDB_API_KEY` — SteamGridDB token fallback if none is stored in keyring

## License

AGPL-3.0
