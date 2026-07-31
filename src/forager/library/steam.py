from __future__ import annotations

import os
import select
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from forager.library.proton import (
    PROTON_APPID,
    PROTON_DEPOTS,
    DEPOTDL_DIR,
    depotdownloader_bin,
    ensure_depotdownloader,
)

try:
    import keyring as _keyring
except Exception:
    _keyring = None

KEYRING_SERVICE = "forager"
KEYRING_USERNAME_KEY = "steam_username"
KEYRING_PASSWORD_KEY = "steam_password"

_GUARD_MARKERS = (
    "steam guard",
    "2 factor auth code",
    "authentication code sent to your email",
)

LOGIN_TIMEOUT = 180.0


def get_username() -> str | None:
    if _keyring is not None:
        try:
            stored = _keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME_KEY)
            if stored:
                return stored
        except Exception:
            pass
    return None


def get_password() -> str | None:
    if _keyring is not None:
        try:
            stored = _keyring.get_password(KEYRING_SERVICE, KEYRING_PASSWORD_KEY)
            if stored:
                return stored
        except Exception:
            pass
    return None


def has_credentials() -> bool:
    return bool(get_username() and get_password())


def set_credentials(username: str, password: str) -> None:
    if _keyring is None:
        raise RuntimeError("keyring backend unavailable")
    _keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME_KEY, username)
    _keyring.set_password(KEYRING_SERVICE, KEYRING_PASSWORD_KEY, password)


def clear_credentials() -> None:
    if _keyring is None:
        return
    for key in (KEYRING_USERNAME_KEY, KEYRING_PASSWORD_KEY):
        try:
            _keyring.delete_password(KEYRING_SERVICE, key)
        except Exception:
            pass


def _login_cmd(username: str, password: str, remember: bool, download_dir: Path) -> list[str]:
    cmd = [
        str(depotdownloader_bin()),
        "-app", PROTON_APPID,
        "-depot", PROTON_DEPOTS[0],
        "-manifest-only",
        "-dir", str(download_dir),
        "-username", username,
        "-password", password,
    ]
    if remember:
        cmd.append("-remember-password")
    return cmd


def verify_login(
    username: str,
    password: str,
    remember: bool,
    guard_prompt,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, str]:
    """Validate Steam credentials with a manifest-only depot download.

    `guard_prompt(message)` is called from this thread whenever Steam Guard
    asks for an auth/email code; it must return the code (or None to cancel).
    Runs DepotDownloader from DEPOTDL_DIR so its `account.config` (refresh
    tokens / sentry data) persists across runs.
    """
    ensure_depotdownloader()
    scratch = Path(tempfile.mkdtemp(prefix="forager-login-"))
    proc: subprocess.Popen | None = None
    try:
        proc = subprocess.Popen(
            _login_cmd(username, password, remember, scratch),
            cwd=str(DEPOTDL_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None and proc.stdin is not None
        fd = proc.stdout.fileno()
        buf = ""
        log: list[str] = []
        cancelled = False
        deadline = threading.Event()
        deadline_timer = threading.Timer(LOGIN_TIMEOUT, deadline.set)
        deadline_timer.start()
        try:
            while proc.poll() is None:
                if deadline.is_set():
                    proc.terminate()
                    break
                if cancel_event is not None and cancel_event.is_set():
                    proc.terminate()
                    break
                r, _, _ = select.select([fd], [], [], 0.5)
                if not r:
                    continue
                data = os.read(fd, 4096)
                if not data:
                    break
                buf += data.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    log.append(line.rstrip())
                    if len(log) > 200:
                        log = log[-100:]
                lower = buf.lower()
                if any(marker in lower for marker in _GUARD_MARKERS):
                    prompt = buf.strip() or "Steam Guard authentication required"
                    code = guard_prompt(prompt)
                    if not code:
                        cancelled = True
                        try:
                            proc.stdin.close()
                        except Exception:
                            pass
                        break
                    try:
                        proc.stdin.write(code + "\n")
                        proc.stdin.flush()
                    except (BrokenPipeError, OSError):
                        break
                    buf = ""
        finally:
            deadline_timer.cancel()

        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        returncode = proc.returncode
        tail = "\n".join(log[-20:]).lower()
        if cancelled or (cancel_event is not None and cancel_event.is_set()):
            return False, "Sign-in cancelled"
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
        shutil.rmtree(scratch, ignore_errors=True)

    if returncode == 0 and "unable to get steam3 credentials" not in tail:
        return True, f"Signed in as {username}"
    return False, tail or f"DepotDownloader exited with code {returncode}"
