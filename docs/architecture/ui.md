# Window / page / widget hierarchy

```
MainWindow (ui/main_window.py)
 ├── TitleBar          ui/widgets/titlebar.py      custom window chrome + menus
 ├── Sidebar           ui/widgets/sidebar.py       search input + account/game list
 ├── RecentPlayedRow   ui/widgets/recent.py        recently-played strip
 └── QStackedWidget    the page stack
      ├── GameGrid     ui/pages/game_grid.py       responsive cover grid
      │     └── GameCard  ui/widgets/game_card.py  one tile
      ├── GamePage     ui/pages/gamepage.py        detail page (banner, play)
      │     └── Banner    ui/widgets/banner.py     blurred hero banner
      ├── DownloadsPage ui/pages/downloads.py      progress bars
      └── StorePage    ui/pages/store.py           prototype store
SettingsDialog (ui/dialogs/settings.py)
 ├── nav sidebar + content stack
 │    ├── LibraryTab  ui/dialogs/settings_tabs.py
 │    ├── ProtonTab   ui/dialogs/settings_tabs.py
 │    └── AccountTab  ui/dialogs/account_tab.py
 ├── SteamAuthDialog          ui/dialogs/steam_auth_dialog.py    QR/device sign-in
 └── SteamGridDBTokenDialog   ui/dialogs/steamgriddb_dialog.py    token entry
GamepadNavigation (ui/widgets/controller_nav.py)  glues evdev gamepad -> UI
```

## Principles

- **`pages/` are the top-level screens** swapped by the page stack; they are
  the only place that assembles composite views.
- **`widgets/` are reusable pieces** (banner, card, spinner, rows, title bar).
  Widgets never know about each other's sibling pages.
- **`dialogs/` are modal flows** (settings, auth). They communicate with the
  main window through signals and explicit return values (e.g.
  `SettingsDialog` exposes `update_proton_requested`, `games_dir_changed`,
  `selected_card_size()`, `games_dir_text()`).
- `theme.py` supplies the shared palette + stylesheet; `icons.py` the themed
  SVG loader; `workers.py` all background threads. See
  [design/theming.md](../design/theming.md) and
  [architecture/threading.md](threading.md).
