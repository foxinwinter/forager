# Build, development and release guide

## Requirements

- Python 3.10+ (development happens on Python 3.14)
- A Steam client install for the Steam library source and its local cover art

## Running from a checkout

```sh
git clone https://github.com/foxinwinter/forager.git
cd forager

python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/forager            # console script from pyproject.toml
```

For a dependency-light checkout you can run straight off the source tree
(no install):

```sh
QT_QPA_PLATFORM=wayland PYTHONPATH=src python -m forager
```

`scripts/run.sh` wraps this for the project maintainer (checks the source tree
exists and runs `python -m forager` with `PYTHONPATH` set).

## Development loop

The test suite runs entirely offscreen (no display server needed):

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python -m pytest -q
```

See [development/testing.md](development/testing.md) for details.

## Building a wheel

```sh
python -m build            # produces dist/forager-<ver>-py3-none-any.whl
```

Package data (`assets/icons/*`, `assets/fonts/*`) is included via
`[tool.setuptools.package-data]` in `pyproject.toml` — resources are resolved
at runtime through `importlib.resources`, so a wheel and a source checkout
behave identically.

## Installing system-wide (Arch Linux example)

Runtime deps come from the distribution to avoid PySide6 conflicts:

```sh
sudo pacman -S python-pyside6 python-evdev python-keyring python-pillow
sudo python -m pip install --break-system-packages --no-deps .
```

- `--break-system-packages` is required on Arch (PEP 668 externally-managed).
- `--no-deps` keeps pacman in charge of dependencies.

## Release process

1. Bump the version in `pyproject.toml` (and `core/constants.py`).
2. Update [changelog.md](changelog.md).
3. Tag on GitHub (`v0.x.y`). Before pushing a tag, run a **local release-prep
   build**: `git archive` the tag to a tarball, build a test PKGBUILD from it
   with `makepkg -f -d`, run `namcap`, and test the resulting `.pkg.tar.zst`.
   See [development/packaging.md](development/packaging.md).

The AUR package (`packaging/forager.desktop`, PKGBUILD in the AUR) follows the
GitHub releases.
