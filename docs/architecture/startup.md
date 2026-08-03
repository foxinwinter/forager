# Startup sequence

```
python -m forager
   └─ forager/__main__.py      -> main()
        └─ forager/main.py     -> ForagerApp(sys.argv)
             └─ forager/app.py -> register_placeholder_font()
                              -> apply_theme(self)     (Fusion style, palette, QSS)
                              -> MainWindow()          (builds sidebar, grid, pages)
                              -> show()
```

1. **`__main__.py`** just delegates to `forager.main:main`.
2. **`main.py`** constructs `ForagerApp`, the `QApplication` subclass in
   `forager/app.py`. (The console-script entry point in `pyproject.toml` is
   `forager.main:main`; both paths land here.)
3. **`ForagerApp.__init__`**:
   - sets application/organisation names (used by Qt settings and keyring);
   - calls `register_placeholder_font()` from `artwork/pipeline.py` to make the
     bundled VT323 font available to `QFontDatabase`;
   - calls `register_ui_font()` (`ui/fonts.py`) to register the bundled
     Be Vietnam Pro weights (SpaceTheme's default UI font);
   - calls `apply_theme()` (`ui/theme.py`) which switches to the Fusion style,
     installs the Be Vietnam Pro default font, builds the palette and installs
     the global stylesheet;
   - constructs and shows `MainWindow`.
4. **`MainWindow`** (`ui/main_window.py`) builds the chrome: custom title bar,
   sidebar (with search), recent-played row, the page stack (library grid,
   game page, downloads, store) and the settings dialog wiring. It then kicks
   off the background scan worker.

The scan itself is asynchronous: `ScanWorker` (`ui/workers.py`) scans the
library on a QThread and emits the game list when done, so startup never blocks
on disk I/O. See [architecture/threading.md](threading.md) and
[architecture/library.md](library.md).
