from forager.core.game import Source
from forager.library import scanner


def _acf(tmp_path, name: str, app_id: str) -> None:
    apps = tmp_path / "steam/steamapps"
    apps.mkdir(parents=True, exist_ok=True)
    acf = apps / f"appmanifest_{app_id}.acf"
    acf.write_text(f'"appid"\t\t"{app_id}"\n"name"\t\t"{name}"\n')


def test_scan_steam(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    _acf(tmp_path, "Half-Life", "70")
    games = scanner._scan_steam()
    assert len(games) == 1
    assert games[0].name == "Half-Life"
    assert games[0].app_id == "70"
    assert games[0].source == Source.STEAM


def test_scan_steam_skips_tools(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    _acf(tmp_path, "Papers, Please", "239030")
    _acf(tmp_path, "Proton Experimental", "1493710")
    _acf(tmp_path, "SteamVR", "250820")
    games = scanner._scan_steam()
    assert [g.name for g in games] == ["Papers, Please"]


def test_scan_minecraft(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    (tmp_path / "minecraft/foo").mkdir(parents=True)
    (tmp_path / "minecraft/.hidden").mkdir(parents=True)
    games = scanner._scan_minecraft()
    assert [g.name for g in games] == ["foo"]


def test_scan_standalone_series(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    (tmp_path / "standalone/series/sequel/asylum").mkdir(parents=True)
    (tmp_path / "standalone/series/sequel/blight").mkdir(parents=True)
    (tmp_path / "standalone/series/sequel/asylum/Game.ini").write_text("[General]\n")
    (tmp_path / "standalone/series/sequel/blight/Game.ini").write_text("[General]\n")
    games = scanner._scan_standalone()
    names = [g.name for g in games]
    assert names == ["sequel/asylum", "sequel/blight"]


def test_scan_drm_free_layout(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    (tmp_path / "drm-free/standalone/other/bdcc").mkdir(parents=True)
    (tmp_path / "drm-free/standalone/other/kludge").mkdir(parents=True)
    (tmp_path / "drm-free/series/rpgMaker/sequel/asylum/Game.ini").parent.mkdir(parents=True)
    (tmp_path / "drm-free/series/rpgMaker/sequel/asylum/Game.ini").write_text("[General]\n")
    (tmp_path / "drm-free/series/unity/furry shades of gay/2/Game.exe").parent.mkdir(parents=True)
    (tmp_path / "drm-free/series/unity/furry shades of gay/2/Game.exe").write_bytes(b"MZ")
    games = scanner._scan_standalone()
    names = sorted(g.name for g in games)
    assert names == ["bdcc", "furry shades of gay/2", "kludge", "sequel/asylum"]
    bdcc = [g for g in games if g.name == "bdcc"][0]
    assert bdcc.search_names == ["Broken Dreams Correctional Center"]


def test_scan_engine_stripped_from_series_names(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    (tmp_path / "drm-free/series/unreal/Some Series/game/Game.exe").parent.mkdir(parents=True)
    (tmp_path / "drm-free/series/unreal/Some Series/game/Game.exe").write_bytes(b"MZ")
    (tmp_path / "drm-free/series/other/Solo/run.sh").parent.mkdir(parents=True)
    (tmp_path / "drm-free/series/other/Solo/run.sh").write_text("#!/bin/sh\n")
    games = scanner._scan_standalone()
    names = sorted(g.name for g in games)
    assert names == ["Solo", "Some Series/game"]


def test_scan_standalone_bdcc_search_names(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    bdcc = tmp_path / "standalone/other/bdcc"
    bdcc.mkdir(parents=True)
    (bdcc / "BDCC.x86_64").write_bytes(b"\x7fELF")
    games = scanner._scan_standalone()
    assert games[0].search_names == ["Broken Dreams Correctional Center"]


def test_scan_all_dedupes(tmp_path, monkeypatch):
    monkeypatch.setattr("forager.library.scanner.games_dir", lambda: tmp_path)
    _acf(tmp_path, "Foo", "1")
    (tmp_path / "minecraft/Foo").mkdir(parents=True)
    bar = tmp_path / "standalone/other/Bar"
    bar.mkdir(parents=True)
    (bar / "run.sh").write_text("#!/bin/sh\n")
    games = scanner.scan_all()
    assert len(games) == 3
