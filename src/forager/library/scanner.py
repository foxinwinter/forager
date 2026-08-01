from __future__ import annotations
import re
from pathlib import Path
from forager.core.game import ENGINE_NAMES, Game, Source
from forager.utils.paths import games_dir

# Steam app IDs that are tools/runtimes rather than games (never shown in
# the library). Proton Experimental is the big one; the Linux runtime
# containers and SteamVR are included so they can't sneak in either.
STEAM_TOOL_APP_IDS = {
    "1493710",  # Proton Experimental
    "250820",   # SteamVR
    "1070560",  # Steam Linux Runtime
    "1391110",  # Steam Linux Runtime - Soldier
    "1628350",  # Steam Linux Runtime - Sniper
}


def scan_all() -> list[Game]:
    seen: set[Game] = set()
    for scanner in (_scan_steam, _scan_minecraft, _scan_standalone):
        for game in scanner():
            if game not in seen:
                seen.add(game)
    return sorted(seen, key=lambda g: g.sort_key or g.name.lower())


def _scan_steam() -> list[Game]:
    games: list[Game] = []
    apps_dir = games_dir() / "steam/steamapps"
    if not apps_dir.is_dir():
        return games

    for acf in sorted(apps_dir.glob("appmanifest_*.acf")):
        app_id, name = _parse_acf(acf)
        if app_id in STEAM_TOOL_APP_IDS:
            continue
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
    mc_dir = games_dir() / "minecraft"
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
    for container in ("standalone", "drm-free"):
        base = games_dir() / container
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if entry.name == "series":
                games.extend(_scan_series_dir(entry))
            else:
                games.extend(_scan_loose_root(entry))
    return games


def _scan_loose_root(root: Path) -> list[Game]:
    """Games directly under root, possibly grouped under an engine folder.

    ``drm-free/standalone/other/bdcc`` -> game ``bdcc``.
    """
    games: list[Game] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if _is_game_dir(entry):
            games.append(_loose_game(entry))
        else:
            games.extend(_scan_loose_flat(entry))
    return games


def _scan_loose_flat(dir: Path) -> list[Game]:
    games: list[Game] = []
    for entry in sorted(dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        games.append(_loose_game(entry))
    return games


def _scan_series_dir(series_root: Path) -> list[Game]:
    """Series games, with an optional engine level that is stripped from names.

    ``series/rpgMaker/sequel/asylum`` -> game ``sequel/asylum``.
    ``series/unity/furry shades of gay/2`` -> game ``furry shades of gay/2``.
    """
    games: list[Game] = []
    for entry in sorted(series_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if _is_game_dir(entry):
            games.append(_loose_game(entry))
            continue
        parts = [] if entry.name.lower() in ENGINE_NAMES else [entry.name]
        _collect_series(entry, parts, games)
    return games


def _is_game_dir(path: Path) -> bool:
    if (path / "Game.ini").is_file():
        return True
    for pattern in ("*.exe", "*.x86_64", "*.sh", "*.py", "icon.png"):
        if next(path.glob(pattern), None) is not None:
            return True
    return False


def _collect_series(path: Path, parts: list[str], out: list[Game]) -> None:
    if _is_game_dir(path):
        rel = "/".join(parts)
        out.append(
            Game(
                name=rel,
                source=Source.STANDALONE,
                path=path,
                sort_key=rel,
            )
        )
        return
    for entry in sorted(path.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            _collect_series(entry, parts + [entry.name], out)


def _loose_game(entry: Path) -> Game:
    kwargs = dict(
        name=entry.name,
        source=Source.STANDALONE,
        path=entry,
        sort_key=entry.name.lower(),
    )
    if entry.name == "bdcc":
        kwargs["search_names"] = ["Broken Dreams Correctional Center"]
    return Game(**kwargs)
