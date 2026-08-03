# Game launch lifecycle

```
MainWindow / GamePage "Play"
   └─ library/launcher.py  launch(game)
        ├─ Source.STEAM      -> steam://rungameid/<appid>
        ├─ Source.MINECRAFT  -> java -jar <instance>/... (or a launcher script)
        └─ Source.STANDALONE -> detect the entry executable
             ├─ .exe          -> compatibility/proton.py  launch_exe()
             └─ .x86_64/.sh/.py -> spawn directly
        └─ library/playtime.py  PlaytimeTracker records the session
```

## Launcher (`library/launcher.py`)

`launch(game)` picks the strategy from `game.source`:

- **Steam** launches via the `steam://rungameid/<app_id>` URI. The command
  returns immediately, so Steam playtime is not accumulated — only the
  last-played stamp is recorded.
- **Minecraft** runs the instance through its launcher.
- **Standalone** finds the executable inside the game folder; `.exe` files are
  run through the shared Proton prefix (`compatibility/proton.py
  launch_exe`), everything else is spawned directly from the game's working
  directory.

## Playtime tracking (`library/playtime.py`)

For launched local processes, a session accumulates playtime while the child
process is alive; `last_played` is stamped at launch so the Recently Played row
works for every source. State persists to `playtime.json` next to
`settings.json` (see [architecture/filesystem.md](filesystem.md)).
