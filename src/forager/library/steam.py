from __future__ import annotations

import os
import re
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
KEYRING_LOGIN_METHOD_KEY = "steam_login_method"

_GUARD_MARKERS = (
    "steam guard",
    "2 factor auth code",
    "authentication code sent to your email",
)

LOGIN_TIMEOUT = 180.0
QR_TIMEOUT = 300.0

_QR_HEADER = "use the steam mobile app to sign in with this qr code:"
_QR_CHANGED = "the qr code has changed:"
_QR_SUCCESS_RE = re.compile(r"-username\s+(\S+)\s+-remember-password\s+instead of\s+-qr")
_SESSION_PROMPT_MARKER = "enter account password for"
_TOKEN_REJECTED_MARKER = "access token was rejected"


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
    return bool(get_username())


def get_login_method() -> str | None:
    """How the stored account signs in: "qr" or "password" (or None)."""
    if _keyring is not None:
        try:
            method = _keyring.get_password(KEYRING_SERVICE, KEYRING_LOGIN_METHOD_KEY)
            if method:
                return method
        except Exception:
            pass
    if get_username() and get_password():
        return "password"
    return None


def set_credentials(username: str, password: str) -> None:
    if _keyring is None:
        raise RuntimeError("keyring backend unavailable")
    _keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME_KEY, username)
    _keyring.set_password(KEYRING_SERVICE, KEYRING_PASSWORD_KEY, password)
    _keyring.set_password(KEYRING_SERVICE, KEYRING_LOGIN_METHOD_KEY, "password")


def set_qr_username(username: str) -> None:
    """Store an account signed in via QR (refresh token lives in
    DepotDownloader's account.config, not the keyring)."""
    if _keyring is None:
        raise RuntimeError("keyring backend unavailable")
    _keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME_KEY, username)
    _keyring.set_password(KEYRING_SERVICE, KEYRING_LOGIN_METHOD_KEY, "qr")
    try:
        _keyring.delete_password(KEYRING_SERVICE, KEYRING_PASSWORD_KEY)
    except Exception:
        pass


def clear_credentials() -> None:
    if _keyring is None:
        return
    for key in (KEYRING_USERNAME_KEY, KEYRING_PASSWORD_KEY, KEYRING_LOGIN_METHOD_KEY):
        try:
            _keyring.delete_password(KEYRING_SERVICE, key)
        except Exception:
            pass


def clear_session() -> None:
    """Drop DepotDownloader's stored sessions (refresh tokens / sentry data)."""
    try:
        cfg = DEPOTDL_DIR / "account.config"
        if cfg.is_file():
            cfg.unlink()
    except OSError:
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


def _qr_cmd(download_dir: Path) -> list[str]:
    return [
        str(depotdownloader_bin()),
        "-app", PROTON_APPID,
        "-depot", PROTON_DEPOTS[0],
        "-manifest-only",
        "-dir", str(download_dir),
        "-qr",
        "-remember-password",
    ]


def _session_cmd(username: str, download_dir: Path) -> list[str]:
    """Reuse a stored refresh token: no password, no Steam Guard."""
    return [
        str(depotdownloader_bin()),
        "-app", PROTON_APPID,
        "-depot", PROTON_DEPOTS[0],
        "-manifest-only",
        "-dir", str(download_dir),
        "-username", username,
        "-remember-password",
    ]


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


def _run_dd(cmd: list[str], timeout: float, cancel_event=None, on_line=None):
    """Run DepotDownloader from DEPOTDL_DIR.

    Calls ``on_line(line)`` for every completed line of combined output.
    Returns ``(log, tail, returncode, cancelled)`` where ``tail`` is the
    trailing line fragment (prompts are written without a newline).
    """
    ensure_depotdownloader()
    proc = subprocess.Popen(
        cmd,
        cwd=str(DEPOTDL_DIR),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    fd = proc.stdout.fileno()
    buf = ""
    log: list[str] = []
    cancelled = False
    deadline = threading.Event()
    deadline_timer = threading.Timer(timeout, deadline.set)
    deadline_timer.start()
    try:
        while proc.poll() is None:
            if deadline.is_set() or (cancel_event is not None and cancel_event.is_set()):
                proc.terminate()
                cancelled = True
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
                line = line.rstrip("\r")
                log.append(line)
                if len(log) > 200:
                    log = log[-100:]
                if on_line is not None:
                    on_line(line)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    finally:
        deadline_timer.cancel()
    return log, buf, proc.returncode, cancelled


def _is_qr_art_line(line: str) -> bool:
    return bool(line) and all(c == " " or 0x2580 <= ord(c) <= 0x259F for c in line)


def parse_qr_art(lines) -> list[list[bool]]:
    """Convert DepotDownloader's ASCII-art QR lines into a bool grid (dark).

    QRCoder renders each module as two characters (``██`` or two spaces), so
    character pairs are collapsed into single cells.
    """
    grid: list[list[bool]] = []
    for line in lines:
        if not line:
            continue
        cells = [c != " " for c in line]
        grid.append([cells[i] or cells[i + 1] for i in range(0, len(cells) - 1, 2)])
    return grid


def login_with_qr(qr_callback, cancel_event: threading.Event | None = None) -> tuple[bool, str]:
    """Sign in via QR code scanned with the Steam mobile app.

    ``qr_callback(art_lines)`` is called each time a QR code is printed
    (initially, and again whenever Steam refreshes the challenge). Returns
    ``(True, account_name)`` on success, or ``(False, reason)``.
    """
    scratch = Path(tempfile.mkdtemp(prefix="forager-qr-"))
    collected: list[str] = []
    collecting = False
    result: list[str] = []

    def on_line(line: str):
        nonlocal collecting
        lowered = line.lower()
        if lowered.startswith(_QR_HEADER) or lowered.startswith(_QR_CHANGED):
            if collected:
                qr_callback(list(collected))
                collected.clear()
            collecting = True
            return
        if collecting:
            if _is_qr_art_line(line):
                collected.append(line)
            else:
                if collected:
                    qr_callback(list(collected))
                    collected.clear()
                collecting = False
        m = _QR_SUCCESS_RE.search(line)
        if m:
            result.append(m.group(1))

    try:
        log, tail, returncode, cancelled = _run_dd(
            _qr_cmd(scratch), QR_TIMEOUT, cancel_event, on_line
        )
        if collecting and collected:
            qr_callback(list(collected))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if result:
        return True, result[0]
    if cancelled:
        return False, "Sign-in cancelled"
    tail = (tail + "\n" + "\n".join(log[-10:])).lower()
    return False, tail or f"DepotDownloader exited with code {returncode}"


def verify_session(username: str, cancel_event: threading.Event | None = None) -> tuple[bool, str]:
    """Validate a previously stored session (refresh token) without a password.

    Returns ``(True, "Signed in as X")`` when DepotDownloader can reuse the
    cached token, or ``(False, reason)`` if the session is gone/rejected.
    """
    scratch = Path(tempfile.mkdtemp(prefix="forager-session-"))
    try:
        log, tail, returncode, cancelled = _run_dd(
            _session_cmd(username, scratch), LOGIN_TIMEOUT, cancel_event
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if cancelled:
        return False, "Check cancelled"
    combined = "\n".join(log[-20:]) + "\n" + tail
    low = combined.lower()
    if _SESSION_PROMPT_MARKER in low:
        return False, "No stored session for this account; sign in again (QR or password)."
    if _TOKEN_REJECTED_MARKER in low:
        return False, "Stored session was rejected; sign in again (QR or password)."
    if returncode == 0 and "unable to get steam3 credentials" not in low:
        return True, f"Signed in as {username}"
    return False, low or f"DepotDownloader exited with code {returncode}"
