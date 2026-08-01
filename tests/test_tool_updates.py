from forager.library import tool_updates
from forager.library.tool_updates import ToolUpdate, check_tool_updates, installed_depotdl_tag


def test_installed_tag_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    assert installed_depotdl_tag() is None


def test_installed_tag_reads_version_file(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("DepotDownloader_3.4.0")
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    assert installed_depotdl_tag() == "DepotDownloader_3.4.0"


def test_installed_tag_blank_file_is_none(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("  \n")
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    assert installed_depotdl_tag() is None


def test_check_no_update_when_current(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("DepotDownloader_3.4.0")
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    monkeypatch.setattr(tool_updates, "_latest_depotdl_tag", lambda: "DepotDownloader_3.4.0")
    assert check_tool_updates() == []


def test_check_reports_newer_release(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("DepotDownloader_3.4.0")
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    monkeypatch.setattr(tool_updates, "_latest_depotdl_tag", lambda: "DepotDownloader_3.5.0")
    assert check_tool_updates() == [
        ToolUpdate("DepotDownloader", "DepotDownloader_3.4.0", "DepotDownloader_3.5.0")
    ]


def test_check_reports_when_not_installed(monkeypatch, tmp_path):
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    monkeypatch.setattr(tool_updates, "_latest_depotdl_tag", lambda: "DepotDownloader_3.5.0")
    assert check_tool_updates() == [
        ToolUpdate("DepotDownloader", None, "DepotDownloader_3.5.0")
    ]


def test_check_no_network_no_update(monkeypatch, tmp_path):
    (tmp_path / "version.txt").write_text("DepotDownloader_3.4.0")
    monkeypatch.setattr(tool_updates, "DEPOTDL_DIR", tmp_path)
    monkeypatch.setattr(tool_updates, "_latest_depotdl_tag", lambda: None)
    assert check_tool_updates() == []
