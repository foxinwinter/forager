# Game discovery & library pipeline

```
games_dir()
   └─ library/scanner.py  scan_all()
        ├─ <games>/steam/            read appmanifest_*.acf  (Source.STEAM)
        ├─ <games>/minecraft/        one folder per instance (Source.MINECRAFT)
        └─ <games>/drm-free/standalone  + series/           (Source.STANDALONE)
             └─ detected by executable (x86_64, .sh, .py, .exe) or Game.ini
        └─ returns list[Game]
             └─ ui/workers.py ScanWorker (QThread) -> MainWindow.set_games()
```

## Scanner (`library/scanner.py`)

`scan_all()` walks the configured games directory and produces `Game`
instances. It never blocks the UI: `ScanWorker` runs it on a worker thread.

- **Steam**: parses `appmanifest_*.acf` files to list installed Steam games.
- **Minecraft**: each folder under `minecraft/` is one instance.
- **Standalone / series**: games live under `standalone/<engine>/<game>` or
  `series/<engine>/<series>/<game>`; a folder counts as a game when it contains
  an executable (`*.x86_64`, `*.sh`, `*.py`, `*.exe`) or a `Game.ini`.
- Tool/runtime folders (e.g. Proton) are filtered out so they never appear in
  the library.

## Game model (`core/game.py`)

Every game is a `Game` dataclass: `name`, `source` (an enum:
`STEAM`/`MINECRAFT`/`STANDALONE`), `path`, plus optional `app_id`,
`launch_cmd`, `search_names`, `sort_key`. See
[api/game.md](../api/game.md).

## Presentation

`MainWindow` hands the games to `GameGrid` (`ui/pages/game_grid.py`) which
filters and sorts them (see `library/metadata.py`) and lazily loads art tiles
through `ArtSignals` workers. `RecentPlayedRow` (`ui/widgets/recent.py`)
renders the most recently played games. Search input comes from the sidebar
(`ui/widgets/sidebar.py`) and is applied via `GameGrid.set_search`.
