# Dependencies

Runtime dependencies declared in `pyproject.toml`:

| Package | Version | Why |
|---------|---------|-----|
| `PySide6` | >= 6.6 | Qt6 bindings for the entire UI |
| `evdev` | >= 1.6 | gamepad input (`core/controller.py`) |
| `keyring` | >= 24 | system keyring for Steam + SteamGridDB secrets |
| `Pillow` | >= 10 | PIL ↔ QPixmap conversion and image processing (`artwork/pixmap_utils.py`) |
| `qrcode` | >= 7 | QR code rendering for Steam mobile sign-in |

Dev/optional: `pytest` (`dev` extra).

## Not yet dependencies (planned)

- `PySide6-WebEngine` — large dependency required for the store webview
  (roadmap item 4); deliberately held back.
- `libtorrent` — torrenting backend (roadmap item 8).

## Bundled, vendored

- **DepotDownloader** and **steamcmd** are downloaded on demand into
  `.runtime/` (see `compatibility/proton.py`) — not Python deps.
- **Icons** are Iconoir SVGs (MIT, © 2021 Luca Burgio) under `assets/icons/`.
- **Fonts** — VT323 (SIL OFL 1.1) under `assets/fonts/`.

## Bundled third-party tools

Proton itself is installed on demand (the user's own copy) into `.runtime/`.
The update check for bundled tools lives in `updates/tool_updates.py`.
