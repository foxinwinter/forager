# Typography

## UI font

- **Be Vietnam Pro** (SpaceTheme's default font; SIL OFL 1.1), 10pt base, set
  as the application font in `ui/theme.py:apply()`. The static weights used by
  the QSS (300/400/500/600/700/800) are bundled in
  `assets/fonts/BeVietnamPro-*.ttf` and registered at startup by
  `register_ui_font()` (`ui/fonts.py`), so the family works offline.
- Weights: 500 default for buttons, 600 for primary actions, 800 for section
  titles (matching SpaceTheme's bold section headers).
- Fallbacks: `"DejaVu Sans", sans-serif` in the global stylesheet.

## Placeholder-art font

- **VT323** (`assets/fonts/VT323-Regular.ttf`, SIL OFL 1.1) is registered at
  startup by `register_placeholder_font()` (`artwork/pipeline.py`) and used
  only by the generated placeholder artwork (`artwork/placeholder.py`) for the
  game-title wordmark — a deliberate retro contrast to the rest of the UI.

## Hierarchy

| Element | Size / weight | Colour |
|---------|---------------|--------|
| Window title | 17px, bold | accent-1 |
| Section title | 13px, weight 800 | blue |
| Body / labels | 13px, 500 | text / muted |
| Secondary / notes | 12px | text-dim |

All values are declared as QSS in the relevant stylesheets; widget code never
hard-codes font sizes — reuse the constants in `ui/theme.py`.
