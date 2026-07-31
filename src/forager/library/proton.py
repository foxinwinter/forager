from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from forager.core.config import settings
from forager.utils.paths import (
    proton_dir,
    proton_prefix_dir,
    rtp_source_dir,
    runtime_dir,
    steam_client_dir,
)

PROTON_APPID = "1493710"
PROTON_DEPOTS = ("1493711", "4862111")
DEPOTDL_URL = "https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_3.4.0/DepotDownloader-linux-x64.zip"
DEPOTDL_DIR = runtime_dir() / "depotdownloader"
STAGING_DIR = runtime_dir() / "proton.new"
BACKUP_DIR = runtime_dir() / "proton.old"

_RTP_RE = re.compile(r"^\s*rtp\s*=\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_RTP_KEY = r"HKLM\Software\Wow6432Node\Enterbrain\RGSS3\RTP"
_RTP_MARKER = ".rtp-done"


def proton_bin() -> Path:
    return proton_dir() / "proton"


def proton_version() -> str | None:
    version_file = proton_dir() / "version"
    if version_file.is_file():
        try:
            return version_file.read_text("utf-8", errors="replace").strip()
        except OSError:
            return None
    return None


def needs_rtp(game_dir: Path) -> bool:
    ini = game_dir / "Game.ini"
    if not ini.is_file():
        return False
    try:
        text = ini.read_text("utf-8", errors="replace")
    except OSError:
        return False
    return _RTP_RE.search(text) is not None


def _proton_env(prefix: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(steam_client_dir())
    env["STEAM_COMPAT_DATA_PATH"] = str(prefix)
    env["WINEDEBUG"] = "-all"
    return env


def ensure_rtp(prefix: Path) -> None:
    source = rtp_source_dir()
    if not source.is_dir():
        return
    marker = prefix / _RTP_MARKER
    if marker.exists():
        return
    prefix.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(proton_bin()), "run", "reg", "add", _RTP_KEY, "/v", "RPGVXAce", "/d", r"C:\rtp", "/f"],
        env=_proton_env(prefix),
        check=True,
    )
    drive_c = prefix / "pfx" / "drive_c"
    drive_c.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, drive_c / "rtp", dirs_exist_ok=True)
    marker.touch()


FEATURES: dict[str, tuple[str, str]] = {
    "rpgmaker_vxace_rtp": ("RPG Maker VX Ace RTP", "Install the shared RTP so RGSS3 games run"),
}


def apply_features(prefix: Path, report=None) -> list[str]:
    """Apply each enabled feature that is not yet marked done in the prefix."""
    applied: list[str] = []
    for name, _ in FEATURES.items():
        if not settings.proton_feature(name):
            continue
        marker = prefix / f".{name}-done"
        if marker.exists():
            continue
        if report is not None:
            report(f"Applying {FEATURES[name][0]}...")
        if name == "rpgmaker_vxace_rtp":
            ensure_rtp(prefix)
        marker.touch()
        applied.append(name)
    return applied


def launch_exe(game_dir: Path, exe: Path) -> subprocess.Popen:
    prefix = proton_prefix_dir()
    prefix.mkdir(parents=True, exist_ok=True)
    if needs_rtp(game_dir):
        apply_features(prefix)
    return subprocess.Popen(
        [str(proton_bin()), "run", str(exe)],
        cwd=game_dir,
        env=_proton_env(prefix),
    )


def depotdownloader_bin() -> Path:
    return DEPOTDL_DIR / "DepotDownloader"


def ensure_depotdownloader() -> None:
    if depotdownloader_bin().is_file():
        return
    DEPOTDL_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DEPOTDL_URL, timeout=120) as resp, tempfile.NamedTemporaryFile(suffix=".zip", dir=runtime_dir()) as tmp:
        shutil.copyfileobj(resp, tmp)
        tmp.flush()
        with zipfile.ZipFile(tmp.name) as zf:
            zf.extractall(DEPOTDL_DIR)
    depotdownloader_bin().chmod(0o755)


def _restore_symlinks(new_dir: Path, ref_dir: Path) -> None:
    """Steampipe strips symlinks to 0-byte placeholders and mode bits;
    restore them from a known-good install so the depot matches a real
    Steam install."""
    for root, dirs, files in os.walk(new_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for d in dirs:
            rel = Path(root).relative_to(new_dir) / d
            ref = ref_dir / rel
            if ref.is_dir():
                try:
                    os.chmod(Path(root) / d, ref.stat().st_mode)
                except OSError:
                    pass
        for name in files:
            path = Path(root) / name
            rel = path.relative_to(new_dir)
            ref = ref_dir / rel
            if path.is_symlink():
                continue
            if ref.is_symlink() and path.stat().st_size == 0:
                path.unlink()
                path.symlink_to(os.readlink(ref))
                continue
            if ref.exists():
                try:
                    os.chmod(path, ref.stat().st_mode)
                except OSError:
                    pass


def update_proton(report=None) -> str | None:
    def emit(msg: str) -> None:
        if report is not None:
            report(msg)

    ensure_depotdownloader()

    emit("Updating Proton...")
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    for depot in PROTON_DEPOTS:
        emit(f"Downloading Proton from Steam (depot {depot})...")
        subprocess.run(
            [
                str(depotdownloader_bin()),
                "-anonymous",
                "-app", PROTON_APPID,
                "-depot", depot,
                "-dir", str(STAGING_DIR),
            ],
            check=True,
        )
    shutil.rmtree(STAGING_DIR / ".DepotDownloader", ignore_errors=True)

    if not (STAGING_DIR / "proton").is_file():
        raise RuntimeError("Downloaded Proton is missing its launcher script")

    emit("Applying patches...")
    _restore_symlinks(STAGING_DIR, proton_dir())

    prefix = proton_prefix_dir()
    if prefix.exists():
        prefix.rename(runtime_dir() / f".prefix-{prefix.name}")

    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    if proton_dir().exists():
        proton_dir().rename(BACKUP_DIR)
    STAGING_DIR.rename(proton_dir())
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)

    saved = runtime_dir() / f".prefix-{prefix.name}"
    if saved.exists():
        saved.rename(proton_dir() / prefix.name)

    version = proton_version()
    emit(f"Proton updated ({version})")
    return version
