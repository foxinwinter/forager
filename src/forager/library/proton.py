from __future__ import annotations
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
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
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
STEAMCMD_DIR = runtime_dir() / "steamcmd"
DEPOTDL_TAG = "DepotDownloader_3.4.0"
DEPOTDL_DIR = runtime_dir() / "depotdownloader"


def depotdl_url(tag: str) -> str:
    return (
        "https://github.com/SteamRE/DepotDownloader/releases/download/"
        f"{tag}/DepotDownloader-linux-x64.zip"
    )


DEPOTDL_URL = depotdl_url(DEPOTDL_TAG)
STAGING_DIR = runtime_dir() / "proton.new"
BACKUP_DIR = runtime_dir() / "proton.old"

_RTP_RE = re.compile(r"^\s*rtp\s*=\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_RTP_KEY = r"HKLM\Software\Wow6432Node\Enterbrain\RGSS3\RTP"
_RTP_MARKER = ".rtp-done"

_PROGRESS_RE = re.compile(
    r"Update state \([0-9a-fx]+\)\s+(\w+), progress:\s*([\d.]+)\s*\((\d+)\s*/\s*(\d+)\)"
)


@dataclass
class DownloadProgress:
    """Structured progress for an active Proton download (bytes/sec speed)."""

    stage: str
    percent: float
    done: int
    total: int
    speed: int = 0


class DownloadCancelled(Exception):
    pass


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
        if not (DEPOTDL_DIR / "version.txt").is_file():
            (DEPOTDL_DIR / "version.txt").write_text(DEPOTDL_TAG, "utf-8")
        return
    DEPOTDL_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DEPOTDL_URL, timeout=120) as resp, tempfile.NamedTemporaryFile(suffix=".zip", dir=runtime_dir()) as tmp:
        shutil.copyfileobj(resp, tmp)
        tmp.flush()
        with zipfile.ZipFile(tmp.name) as zf:
            zf.extractall(DEPOTDL_DIR)
    depotdownloader_bin().chmod(0o755)
    (DEPOTDL_DIR / "version.txt").write_text(DEPOTDL_TAG, "utf-8")


def steamcmd_sh() -> Path:
    return STEAMCMD_DIR / "steamcmd.sh"


def ensure_steamcmd() -> None:
    """Provision the official Valve steamcmd (used to install Proton with
    symlinks intact, which DepotDownloader cannot do)."""
    if steamcmd_sh().is_file():
        return
    STEAMCMD_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(STEAMCMD_URL, timeout=120) as resp, tempfile.NamedTemporaryFile(suffix=".tar.gz", dir=runtime_dir()) as tmp:
        shutil.copyfileobj(resp, tmp)
        tmp.flush()
        with tarfile.open(tmp.name) as tf:
            tf.extractall(STEAMCMD_DIR)
    steamcmd_sh().chmod(0o755)
    (STEAMCMD_DIR / "linux32" / "steamcmd").chmod(0o755)


def _verify_symlinks(new_dir: Path) -> None:
    """Fail fast if symlinks were flattened to 0-byte placeholders."""
    msidb = new_dir / "files" / "bin" / "msidb"
    if not msidb.is_symlink():
        raise RuntimeError("Proton download did not preserve symlinks")


def _restore_exec_bits(new_dir: Path) -> None:
    launcher = new_dir / "proton"
    if launcher.is_file():
        try:
            launcher.chmod(0o755)
        except OSError:
            pass
    for sub in ("files/bin", "files/lib/wine"):
        base = new_dir / sub
        if not base.is_dir():
            continue
        for root, _dirs, files in os.walk(base):
            for name in files:
                path = Path(root) / name
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    path.chmod(0o755)
                except OSError:
                    pass


def update_proton(report=None, on_progress=None, cancel_event=None) -> str | None:
    def emit(msg: str) -> None:
        if report is not None:
            report(msg)

    ensure_steamcmd()

    emit("Updating Proton...")
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    emit("Downloading Proton from Steam...")
    proc = subprocess.Popen(
        [
            str(steamcmd_sh()),
            "+@ShutdownOnFailedCommand", "1",
            "+@NoPromptForPassword", "1",
            "+login", "anonymous",
            "+force_install_dir", str(STAGING_DIR),
            "+app_update", PROTON_APPID, "validate",
            "+quit",
        ],
        cwd=str(STEAMCMD_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    last_done: int | None = None
    last_t: float | None = None
    speed = 0
    for line in proc.stdout:
        m = _PROGRESS_RE.search(line)
        if m:
            stage = m.group(1).capitalize()
            percent = float(m.group(2))
            done, total = int(m.group(3)), int(m.group(4))
            now = time.monotonic()
            if last_done is not None and last_t is not None:
                dt = now - last_t
                if dt > 0:
                    speed = int((done - last_done) / dt)
            last_done, last_t = done, now
            if on_progress is not None:
                on_progress(DownloadProgress(stage, percent, done, total, speed))
        if cancel_event is not None and cancel_event.is_set():
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            raise DownloadCancelled("Download cancelled")
    returncode = proc.wait()
    if returncode != 0:
        raise RuntimeError(f"steamcmd exited with code {returncode}")

    if not (STAGING_DIR / "proton").is_file():
        raise RuntimeError("Downloaded Proton is missing its launcher script")
    _verify_symlinks(STAGING_DIR)
    shutil.rmtree(STAGING_DIR / "steamapps", ignore_errors=True)

    emit("Applying patches...")
    _restore_exec_bits(STAGING_DIR)

    saved_pfx = runtime_dir() / ".prefix-pfx"
    pfx = proton_dir() / "files" / "pfx"
    if pfx.exists():
        pfx.rename(saved_pfx)

    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    if proton_dir().exists():
        proton_dir().rename(BACKUP_DIR)
    STAGING_DIR.rename(proton_dir())
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)

    if saved_pfx.exists():
        new_pfx = proton_dir() / "files" / "pfx"
        new_pfx.parent.mkdir(parents=True, exist_ok=True)
        saved_pfx.rename(new_pfx)

    version = proton_version()
    emit(f"Proton updated ({version})")
    return version
