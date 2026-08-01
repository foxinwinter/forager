"""Update detection for the third-party tools forager provisions.

Only DepotDownloader is checked: it is pinned to a fixed GitHub release
(``DEPOTDL_TAG``) and GitHub publishes a versioned tag per release, so a newer
one is always discoverable. steamcmd is deliberately not checked — Valve ships
a single unversioned tarball and the binary self-updates on every run, so the
copy on disk is always current after any use.
"""
from __future__ import annotations
import json
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from forager.library.proton import (
    DEPOTDL_DIR,
    depotdl_url,
    depotdownloader_bin,
    runtime_dir,
)

GITHUB_LATEST_URL = (
    "https://api.github.com/repos/SteamRE/DepotDownloader/releases/latest"
)


@dataclass
class ToolUpdate:
    name: str
    installed: str | None
    latest: str


def installed_depotdl_tag() -> str | None:
    version_file = DEPOTDL_DIR / "version.txt"
    if not version_file.is_file():
        return None
    try:
        text = version_file.read_text("utf-8", errors="replace").strip()
    except OSError:
        return None
    return text or None


def _latest_depotdl_tag() -> str | None:
    req = urllib.request.Request(GITHUB_LATEST_URL, headers={"User-Agent": "forager"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except (OSError, ValueError):
        return None
    tag = data.get("tag_name")
    return tag if isinstance(tag, str) and tag else None


def check_tool_updates() -> list[ToolUpdate]:
    """Tools with a newer release available (network failure => no updates)."""
    latest = _latest_depotdl_tag()
    if latest is None:
        return []
    installed = installed_depotdl_tag()
    if installed == latest:
        return []
    return [ToolUpdate("DepotDownloader", installed, latest)]


def update_tool_updates(report=None) -> list[str]:
    """Fetch the latest release of every outdated tool. Returns updated names."""
    updated: list[str] = []
    for update in check_tool_updates():
        if report is not None:
            report(f"Updating {update.name}...")
        _download_depotdl(update.latest)
        updated.append(update.name)
    return updated


def _download_depotdl(tag: str) -> None:
    DEPOTDL_DIR.mkdir(parents=True, exist_ok=True)
    for old in DEPOTDL_DIR.iterdir():
        if old.is_dir():
            shutil.rmtree(old, ignore_errors=True)
        else:
            old.unlink()
    with urllib.request.urlopen(depotdl_url(tag), timeout=120) as resp, tempfile.NamedTemporaryFile(suffix=".zip", dir=runtime_dir()) as tmp:
        shutil.copyfileobj(resp, tmp)
        tmp.flush()
        with zipfile.ZipFile(tmp.name) as zf:
            zf.extractall(DEPOTDL_DIR)
    depotdownloader_bin().chmod(0o755)
    (DEPOTDL_DIR / "version.txt").write_text(tag, "utf-8")
