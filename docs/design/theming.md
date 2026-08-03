# Theming

## Palette (`ui/theme.py`)

The `C` class is the single source of colour truth (SpaceTheme palette):

```
BG #0a0a0a      COLOR_1 #111111   COLOR_2 #1e1e1e   COLOR_3 #141414
COLOR_4 #181818  COLOR_5 #26292c   COLOR_6 #262629
ACCENT_1 #666cff  ACCENT_2 #878cff
BLUE #4b89ef      BLUE_HOVER #649af2
GREEN #24a65a     GREEN_HOVER #27b964
RED #f04a4a       RED_HOVER #f26363
TEXT #ffffff      TEXT_DIM #8e8e8e  TEXT_MUTED #a3aab9
RADIUS = 8
```

Plus `PAGE_BG` (the subtle vertical gradient behind pages), `PANEL_QSS`,
`TAB_QSS` and `NAV_TAB_QSS`.

## Applying the theme

`ui/theme.py:apply(app)` runs once at startup (`app.py`):

1. `app.setStyle("Fusion")` — the platform style base.
2. Install the Roboto font.
3. Build a `QPalette` from the `C` palette (Window/Base/Text/Highlight/…).
4. Install the global stylesheet (`stylesheet()`): backgrounds, QPushButton,
   QLineEdit, scrollbars, menus, tooltips, dialogs.

## Icon tinting (`ui/icons.py`)

Bundled Iconoir SVGs use `currentColor`. `load_icon(name, color)` replaces
`stroke="currentColor"` / `fill="currentColor"` with the requested colour
(default `C.TEXT`) and caches the resulting `QIcon` per `(name, color)`.
Navigation icons additionally swap between an off-state (`#b8bcbf`) and an
on-state (accent) via a two-pixmap `QIcon` (see `ui/dialogs/settings.py`).

## Rules for UI code

- Reference `C.*` / the shared QSS — never hard-code hex in widgets.
- Section/row styling is centralised (blue weight-800 titles over COLOR_3
  cards with COLOR_2 rows) via the helpers in `ui/dialogs/settings_tabs.py`.
