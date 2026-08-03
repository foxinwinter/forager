# Packaging & release process

## Packaging

- `pyproject.toml` (setuptools): name `forager`, version, runtime deps
  (`PySide6`, `evdev`, `keyring`, `Pillow`, `qrcode`), a `forager` console
  script, and package-data globs for `assets/icons/*` and `assets/fonts/*`.
- `packaging/forager.desktop` — freedesktop launcher entry.
- AUR: the official Arch package installs the wheel into the system Python
  with pacman-owned runtime deps (see [build.md](../build.md)).

## Building a wheel

```sh
python -m build
```

Sanity-check the wheel's contents include `assets/icons/*.svg`,
`assets/fonts/*.ttf` and all packages.

## Release checklist

1. Bump `version` in `pyproject.toml` and `VERSION` in `core/constants.py`.
2. Update `docs/changelog.md`.
3. **Local release-prep build (required before tagging):**
   - `git archive --format=tar.gz --prefix=forager-<ver>/ -o forager-<ver>.tar.gz HEAD`
   - point a test PKGBUILD at that tarball and `makepkg -f -d` in a scratch dir
   - run `namcap` on the result; it must be clean (fix missing deps it flags)
   - hand the user the `.pkg.tar.zst` to test.
4. Tag `v0.x.y` on GitHub and attach the wheel; the AUR follows.

## What shipping a change touches

- Source + tests, both the authored and the mirrored checkout, committed
  together with the same message (maintainer rule — the project uses two
  byte-identical checkouts with separate git repos, committed with the same
  message).
- Docs under `docs/` whenever layout or behaviour changes.
