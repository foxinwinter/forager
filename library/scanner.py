from __future__ import annotations
import re
from pathlib import Path
from library.game import Game, Source

GAMES_DIR = Path("/nyaa/games")


def scan_all() -> list[Game]:
    seen: set[Game] = set()
    for scanner in (_scan_steam, _scan_minecraft, _scan_standalone):
        for game in scanner():
            if game not in seen:
                seen.add(game)
    return sorted(seen, key=lambda g: g.sort_key or g.name.lower())


def _scan_steam() -> list[Game]:
    games: list[Game] = []
    apps_dir = GAMES_DIR / "steam/steamapps"
    if not apps_dir.is_dir():
        return games

    for acf in sorted(apps_dir.glob("appmanifest_*.acf")):
        app_id, name = _parse_acf(acf)
        if app_id and name:
            games.append(
                Game(
                    name=name,
                    source=Source.STEAM,
                    path=apps_dir / "common" / name,
                    app_id=app_id,
                    sort_key=name.lower(),
                )
            )
    return games


def _parse_acf(path: Path) -> tuple[str | None, str | None]:
    try:
        text = path.read_text("utf-8", errors="replace")
        app_id = _acf_val(text, "appid")
        name = _acf_val(text, "name")
        if name:
            name = name.removesuffix("\u0000")
        return (app_id, name)
    except Exception:
        return (None, None)


def _acf_val(text: str, key: str) -> str | None:
    m = re.search(rf'"{re.escape(key)}"\s+"(.+?)"', text)
    if m:
        return m.group(1)
    return None


def _scan_minecraft() -> list[Game]:
    games: list[Game] = []
    mc_dir = GAMES_DIR / "minecraft"
    if not mc_dir.is_dir():
        return games

    for entry in sorted(mc_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == ".LAUNCHER_TEMP":
            continue
        games.append(
            Game(
                name=entry.name,
                source=Source.MINECRAFT,
                path=entry,
                sort_key=entry.name.lower(),
            )
        )
    return games


def _scan_standalone() -> list[Game]:
    games: list[Game] = []
    sd_dir = GAMES_DIR / "standalone"
    if not sd_dir.is_dir():
        return games

    for entry in sorted(sd_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name == "series":
            for series_dir in sorted(entry.iterdir()):
                if not series_dir.is_dir() or series_dir.name.startswith("."):
                    continue
                for game_dir in sorted(series_dir.iterdir()):
                    if not game_dir.is_dir() or game_dir.name.startswith("."):
                        continue
                    games.append(
                        Game(
                            name=f"{series_dir.name}/{game_dir.name}",
                            source=Source.STANDALONE,
                            path=game_dir,
                            sort_key=f"{series_dir.name}/{game_dir.name}",
                        )
                    )
        else:
            kwargs = dict(
                name=entry.name,
                source=Source.STANDALONE,
                path=entry,
                sort_key=entry.name.lower(),
            )
            if entry.name == "bdcc":
                kwargs["search_names"] = ["Broken Dreams Correctional Center"]
            games.append(Game(**kwargs))
    return games
