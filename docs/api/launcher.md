# Launcher API — reference

Source: `src/forager/library/launcher.py`

```python
def launch(game: Game) -> subprocess.Popen | None
```

Launches *game* based on `game.source`:

- `Source.STEAM` → `steam://rungameid/<app_id>` (returns a handle that exits
  immediately; only `last_played` is recorded).
- `Source.MINECRAFT` → runs the instance launcher.
- `Source.STANDALONE` → spawns the entry executable from the game folder;
  `.exe` files run through the shared Proton prefix
  (`compatibility/proton.launch_exe`), everything else directly.

Returns the `Popen` for local processes, `None` when nothing could be started.

## Playtime

`library/playtime.py` exposes `PlaytimeTracker` (session tracking while the
child lives), `PlaytimeStore` (persistence to `playtime.json`), plus
`format_playtime` / `game_key` helpers used by the Recently Played row.

## Related

- [architecture/launcher.md](../architecture/launcher.md)
- [api/game.md](game.md) (`Source`, `launch_cmd`)
