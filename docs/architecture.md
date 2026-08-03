# Architecture overview

forager is a PySide6 desktop application: a Steam-style launcher for a local
game library. It is organised around a few clear layers, mirroring the source
layout under `src/forager/`:

```
┌───────────────────────────────────────────────────────────────┐
│ ui/            all visible surface                            │
│   main_window / pages / widgets / dialogs / theme / workers   │
├───────────────────────────────────────────────────────────────┤
│ library/       core game-domain logic (scan, launch, playtime)│
│ artwork/       art fetching + generation pipeline             │
│ providers/     per-store integrations (steam, epic, gog, ...) │
│ services/      online services (SteamGridDB, icon provider)   │
│ compatibility/ third-party runtime management (Proton)        │
│ updates/       bundled-tool update checks                     │
├───────────────────────────────────────────────────────────────┤
│ core/          app-agnostic plumbing: config, paths, game model│
│ utils/         small shared helpers                            │
└───────────────────────────────────────────────────────────────┘
```

The layout is documented per-package in
[development/project_layout.md](development/project_layout.md).

## Key ideas

- **Everything off the GUI thread.** Network and disk work happens in
  `ui/workers.py` QThreads (or plain Python threads for login flows), each
  carrying a stop `Event` so shutdown is clean. See
  [architecture/threading.md](architecture/threading.md).
- **Games are plain data.** A `Game` dataclass (`core/game.py`) is produced by
  the scanner and consumed everywhere: the grid, the game page, the launcher,
  the art pipeline. See [api/game.md](api/game.md).
- **Art has a strict resolution order** (local Steam appcache → disk cache →
  Steam CDN → SteamGridDB by id → by search → generated placeholders), so the
  app degrades gracefully offline. See [architecture/artwork.md](architecture/artwork.md).
- **Theming is centralised.** The `C` palette in `ui/theme.py` (SpaceTheme
  colours) drives the global stylesheet, and bundled icons are recoloured at
  load time. See [design/theming.md](design/theming.md).
- **Settings live in one JSON file.** `core/config.py` deep-merges user
  settings over defaults. See [architecture/settings.md](architecture/settings.md).

## Where the roadmap touches the code

Owned library, downloads, achievements, Epic and GOG all plug in at the
**provider** layer (`providers/`); the download page (`ui/pages/downloads.py`)
already renders progress and can be driven by any of them. See
[docs/roadmap.md](roadmap.md) and [providers](providers/steam.md).
