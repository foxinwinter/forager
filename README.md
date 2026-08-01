# forager

A Steam-style game launcher for your local game library.

## Features

- **Library view** — Steam-style grid of cover tiles with a searchable
  sidebar game list.
- **Gamepad support** — navigate and launch with a controller (via `evdev`).
- **Cover art** — pulls portrait grid art, headers, banners, and icons from
  local Steam files, the Steam CDN, and SteamGridDB (token stored in your
  system keyring).
- **Steam account** — sign in with the Steam mobile app (QR code) or
  username/password; the session persists in your system keyring.
- **Proton** — runs standalone Windows `.exe` games through a single shared
  Proton prefix. Add extras to the prefix (e.g. the RPG Maker VX Ace RTP) from
  the Settings dialog.
- **Tool updates** — keeps the bundled tools up to date with live progress on
  the downloads page.

## Roadmap

See [roadmap.md](roadmap.md) for the plan towards `v1.0.0` (full Steam library,
Steam downloads, store webview, torrenting, Steam achievements, Epic Games, GOG).

## Layout

Your game library folder is expected to look like:

```
~/Games/
├── steam/
│   └── steamapps/            # appmanifest_*.acf + common/<name>
├── minecraft/                # one folder per Minecraft instance
└── drm-free/
    ├── standalone/
    │   └── <engine>/         # engine group: other, rpgMaker, unity, unreal
    │       └── <game>/       # standalone games (finds *.x86_64, *.sh, *.py, *.exe)
    └── series/
        └── <engine>/
            └── <series>/
                └── <game>/   # games grouped by series
```

Games grouped by their engine (`rpgMaker`, `unity`, `unreal`, `other`) under
`standalone/` (single games) and `series/` (series games). Games are detected
by an executable or `Game.ini` in the folder.

## Install

### From the AUR (Arch Linux)

```sh
paru -S forager
# or: yay -S forager
```

### Manual

Requirements: Python 3.10+ and a Steam client install (for the Steam library
source and its local cover art).

From source:

```sh
git clone https://github.com/foxinwinter/forager.git
cd forager
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/forager
```

Or install a release wheel — download the `forager-<version>-py3-none-any.whl`
asset from the [latest release](https://github.com/foxinwinter/forager/releases)
and run:

```sh
pip install forager-<version>-py3-none-any.whl
forager
```

## Configuration

Settings are stored in `~/.config/forager/settings.json`; cover art caches live
in `~/.cache/forager/`. Open the **forager → Settings…** menu to change the game
library folder, the Steam appcache/librarycache folder, the card size, the
Steam account, and which extras get added to the Proton prefix.

Environment overrides:

- `FORAGER_CONFIG_DIR` — config directory (default `~/.config/forager`)
- `FORAGER_CACHE_DIR` — cache directory (default `~/.cache/forager`)
- `STEAMGRIDDB_API_KEY` — SteamGridDB token fallback if none is stored in keyring

## License

AGPL-3.0
