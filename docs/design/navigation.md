# Navigation

## Main window

- **Sidebar** (`ui/widgets/sidebar.py`) — the primary rail: search box, the
  game list, and the account entry point. Selecting a game opens its page;
  searching filters the library grid and the recently-played row live.
- **Page stack** — `MainWindow` holds a `QStackedWidget`:
  - **Library** (`ui/pages/game_grid.py`) — the default view: responsive grid
    of cover tiles.
  - **Game page** (`ui/pages/gamepage.py`) — banner + hero art, launch button,
    back navigation to the library.
  - **Downloads** (`ui/pages/downloads.py`) — tool update progress.
  - **Store** (`ui/pages/store.py`) — prototype.
- **Title bar** (`ui/widgets/titlebar.py`) — custom chrome with the app menu
  (including **Settings…** and **Update Proton**).

## Settings dialog

`ui/dialogs/settings.py` uses a nav-list pattern: a fixed sidebar with
icon+label items (Library / Proton / Account) and a content stack. The checked
item is shown with an accent left-border and accent text.

## Gamepad

`GamepadNavigation` (`ui/widgets/controller_nav.py`) maps `evdev` gamepad
events onto the same actions the mouse/keyboard perform, so the whole flow
(select → open → play) works hands-free.

## Design principles

- One action per screen, one way to reach it (no buried menus).
- Page changes are immediate; never block on network/disk (background workers).
- Back is always one press away on the game page.
