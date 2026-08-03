# Project layout — every package explained

Source root: `src/forager/`

| Package | Purpose |
|---------|---------|
| `main.py` | application entrypoint (`main()`), constructs `ForagerApp` |
| `__main__.py` | `python -m forager` delegation |
| `app.py` | `ForagerApp(QApplication)` — startup wiring (font, theme, window) |
| `core/` | app-agnostic plumbing |
| `core/config.py` | `Settings` (settings.json), defaults, dir overrides |
| `core/constants.py` | app/version/keyring constants |
| `core/controller.py` | gamepad detection + `ControllerPoller` QThread |
| `core/game.py` | `Game` dataclass, `Source` enum, desktop-file parsing |
| `core/paths.py` | filesystem locations (games dir, runtime dirs, assets) |
| `library/` | core game-domain logic (no Qt, no UI) |
| `library/scanner.py` | discover installed games (`scan_all`) |
| `library/launcher.py` | launch games by source |
| `library/playtime.py` | playtime/session tracking (`playtime.json`) |
| `library/metadata.py` | search matching + sorting helpers for the game list |
| `artwork/` | art fetching + generation |
| `artwork/pipeline.py` | complete artwork pipeline (header/grid/hero/logo) |
| `artwork/placeholder.py` | generated fallback artwork (VT323 title) |
| `artwork/pe_icons.py` | extract icons from PE executables |
| `artwork/pixmap_utils.py` | PIL ↔ QPixmap helpers, scaling |
| `artwork/cache.py` | artwork cache directory management |
| `providers/` | per-store integrations |
| `providers/steam/` | Steam: `account.py`, `auth.py`, `appid.py` + planned `library.py`, `downloader.py`, `achievements.py` |
| `providers/epic/`, `gog/`, `torrent/` | placeholder packages (roadmap) |
| `services/` | online services used by the art pipeline |
| `services/steamgriddb.py` | SteamGridDB API v2 client |
| `services/icon_provider.py` | icon fetching + caching |
| `compatibility/` | third-party runtime management |
| `compatibility/proton.py` | Proton install/manage, shared prefix, DepotDownloader/steamcmd |
| `updates/` | bundled-tool update checks |
| `updates/tool_updates.py` | DepotDownloader update detection |
| `ui/` | all visible surface |
| `ui/theme.py` | palette (`C`), global QSS, `apply()` |
| `ui/icons.py` | themed SVG icon loader |
| `ui/workers.py` | background QThreads + job functions |
| `ui/main_window.py` | main window, page stack, wiring |
| `ui/pages/` | top-level screens: `downloads.py`, `game_grid.py`, `gamepage.py`, `store.py` |
| `ui/widgets/` | reusable pieces: `banner.py`, `controller_nav.py`, `game_card.py`, `loading_spinner.py`, `recent.py`, `sidebar.py`, `titlebar.py` |
| `ui/dialogs/` | modal flows: `settings.py`, `settings_tabs.py`, `account_tab.py`, `steam_auth_dialog.py`, `steamgriddb_dialog.py` |
| `utils/` | small shared helpers: `filesystem.py`, `network.py`, `subprocess.py`, `threading.py` |
| `assets/` | packaged data: `fonts/` (VT323), `icons/` (Iconoir SVGs) |

Tests live in `tests/` (not shipped; gitignored).
