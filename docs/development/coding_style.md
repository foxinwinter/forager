# Coding style

The codebase follows these conventions:

## Python

- `from __future__ import annotations` at the top of every module.
- Full type hints on every function signature; `dict[str, str]`-style builtin
  generics (Python 3.10+).
- Data models are `@dataclass` (see `core/game.py`); enums use
  `enum.Enum`/`auto` (`core/game.py:Source`).
- Import style: stdlib first, then third-party, then `forager.*`. Alias
  package/module imports only when needed for clarity or compatibility.
- No comments unless they explain *why*; use docstrings for module and public
  function intent (a few "how" comments exist in tricky code, e.g. output
  reading loops).

## Qt / UI

- Widgets are styled via the global stylesheet in `ui/theme.py` plus small
  local `_QSS` string constants; **never** hard-code colors inside widgets —
  always reference the `C` palette.
- Icons: use `ui/icons.load_icon(name, color)` with a `C` color; bundled
  SVGs are Iconoir *regular* with `currentColor` strokes.
- Reusable views go in `ui/widgets/`, screens in `ui/pages/`, modals in
  `ui/dialogs/`. Widgets must not reach into sibling pages.
- Off-GUI-thread work goes through `ui/workers.py`; UI mutation always happens
  on the main thread via Qt signals.

## Naming

- Modules/functions: `snake_case`; classes `PascalCase`; constants `UPPER`.
- Private helpers start with `_`; module-private constants like `_GUARD_MARKERS`.
- Test files mirror the module they test (`test_scanner.py` ↔
  `library/scanner.py`).

## Verification

Before pushing, run:

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest -q
```

No linter/formatter is configured beyond this; match the surrounding style.
