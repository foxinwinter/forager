# Worker threads, signals & cancellation

## Rule

Network and disk work never runs on the GUI thread.

## Workers (`ui/workers.py`)

- `ScanWorker` — scans the library (`library/scanner.py`), emits the game list
  when done.
- `ProtonUpdateWorker` — downloads/installs a new Proton release, emitting
  `message`, `progress` and `done` signals.
- `TestDownloadWorker` — fake progress for exercising the downloads UI.
- `ToolUpdateWorker` — updates bundled tools; `_tool_update_check_job` checks
  for updates without blocking.
- `_art_job` / `_hero_job` — background art fetching (grid/hero bytes), emitted
  per-game via `ArtSignals` / `HeroSignals`.

Each worker exposes a stop `threading.Event` (or uses
`QThread.isInterruptionRequested()`); the window sets it on shutdown so
workers exit promptly and Qt never destroys a still-running thread.

## Other threads

- **Steam login / session verification** (`providers/steam/account.py`): plain
  Python threads drive DepotDownloader subprocesses, reading output line by
  line and calling back for Steam Guard prompts; guarded by `LOGIN_TIMEOUT`
  timers and a cancel `Event`.
- **Gamepad** (`core/controller.py`): `ControllerPoller` is a QThread polling
  `evdev` for gamepad events, bridged to the UI by
  `ui/widgets/controller_nav.py`.

## Signal conventions

QThread workers emit Qt `Signal`s (declared on the worker class). Job
functions communicate through tiny signal-objects (`ToolUpdateSignals`,
`ArtSignals`, `HeroSignals`) so they can be called from any thread. UI updates
always happen on the main thread via signals — never by mutating widgets from a
worker.
