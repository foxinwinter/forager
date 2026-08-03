# Changelog

## Unreleased

- UI font switched from Roboto to **Be Vietnam Pro** (SpaceTheme's default).
  The OFL-licensed static weights (300/400/500/600/700/800) are bundled in
  `assets/fonts/` and registered at startup by `ui/fonts.py`, so the theme now
  matches without a network dependency.

## 0.2.0 — 2026-08-02

- Major source reorganisation into a layered layout (`artwork/`, `providers/`,
  `services/`, `compatibility/`, `updates/`, `utils/`), with a full `docs/`
  tree. Behaviour is unchanged.
- SpaceTheme-style Settings dialog redesign (fixed a crash on open; new
  header/sidebar/footer shell, reworked tab sections, bundled nav icons).

## 0.1.1 — 2026-07-31

- Fixed PE-icon extraction on high-DPI/cropped tiles and enlarged grid text.

## 0.1.0 — 2026-07-31

- First tagged release: initial launcher, library grid, art pipeline, Steam
  sign-in, Proton support, tool updates.
