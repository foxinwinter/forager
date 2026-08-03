# Contributing

## Coding standards

The conventions are documented in [development/coding_style.md](development/coding_style.md).
In short:

- `from __future__ import annotations` at the top of every module.
- Type hints everywhere; dataclasses for data models.
- No comments unless they explain *why*; prefer clear names and docstrings.
- Follow the existing package layout; new domain code goes under
  `core/`, `library/`, `providers/`, `services/`, `compatibility/` or
  `updates/`, never in `ui/`.

## What to work on

The [roadmap](roadmap.md) is the source of truth. Good entry points:

- New providers (Epic, GOG, torrenting) have scaffolded packages under
  `src/forager/providers/` with design-note docs under `docs/providers/`.
- Anything marked *Planned* in `docs/roadmap.md`.

## Testing

Every change must keep the suite green:

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest -q
```

See [development/testing.md](development/testing.md) for the testing model and
for how UI code is exercised without a display.

## Documentation

- Update the relevant page under `docs/` when a change affects behaviour or
  layout (the index is `docs/README.md`).
- Keep diagrams (`docs/diagrams/*.mmd`) in sync with the code.
- When a public API changes, update the matching page under `docs/api/`.

## Commit conventions

- Concise, imperative summaries (e.g. `feat: …`, `fix: …`, `chore: …`).
- A new commit per logical change; no sweeping unrelated edits in one commit.
- Both the authored and the mirrored checkout are committed together with the
  same message (maintainer rule — the project uses two byte-identical
  checkouts with separate git repos, committed with the same message).
