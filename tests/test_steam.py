from pathlib import Path

from forager.library import steam


class FakeKeyring:
    def __init__(self):
        self._store = {}

    def set_password(self, service, user, password):
        self._store[(service, user)] = password

    def get_password(self, service, user):
        return self._store.get((service, user))

    def delete_password(self, service, user):
        self._store.pop((service, user), None)


def test_credentials_roundtrip(monkeypatch):
    keyring = FakeKeyring()
    monkeypatch.setattr(steam, "_keyring", keyring)
    assert not steam.has_credentials()
    steam.set_credentials("alice", "hunter2")
    assert steam.get_username() == "alice"
    assert steam.get_password() == "hunter2"
    assert steam.has_credentials()
    steam.clear_credentials()
    assert steam.get_username() is None
    assert steam.get_password() is None
    assert not steam.has_credentials()


def test_credentials_no_keyring(monkeypatch):
    monkeypatch.setattr(steam, "_keyring", None)
    assert steam.get_username() is None
    assert steam.get_password() is None
    assert not steam.has_credentials()


def test_login_cmd(monkeypatch):
    monkeypatch.setattr(steam, "depotdownloader_bin", lambda: Path("/bin/depotdownloader"))
    cmd = steam._login_cmd("alice", "hunter2", False, Path("/tmp/dl"))
    assert cmd[0] == "/bin/depotdownloader"
    assert "-app" in cmd and "-depot" in cmd and "-manifest-only" in cmd
    assert cmd[cmd.index("-username") + 1] == "alice"
    assert cmd[cmd.index("-password") + 1] == "hunter2"
    assert "-remember-password" not in cmd
    cmd2 = steam._login_cmd("alice", "hunter2", True, Path("/tmp/dl"))
    assert "-remember-password" in cmd2


def test_qr_cmd(monkeypatch):
    monkeypatch.setattr(steam, "depotdownloader_bin", lambda: Path("/bin/depotdownloader"))
    cmd = steam._qr_cmd(Path("/tmp/dl"))
    assert "-qr" in cmd and "-remember-password" in cmd
    assert "-username" not in cmd and "-password" not in cmd


def test_session_cmd(monkeypatch):
    monkeypatch.setattr(steam, "depotdownloader_bin", lambda: Path("/bin/depotdownloader"))
    cmd = steam._session_cmd("alice", Path("/tmp/dl"))
    assert cmd[cmd.index("-username") + 1] == "alice"
    assert "-remember-password" in cmd
    assert "-password" not in cmd and "-qr" not in cmd


def test_login_method_roundtrip(monkeypatch):
    keyring = FakeKeyring()
    monkeypatch.setattr(steam, "_keyring", keyring)
    assert steam.get_login_method() is None
    steam.set_credentials("alice", "hunter2")
    assert steam.get_login_method() == "password"
    steam.set_qr_username("alice")
    assert steam.get_username() == "alice"
    assert steam.get_password() is None
    assert steam.has_credentials()
    assert steam.get_login_method() == "qr"
    steam.clear_credentials()
    assert steam.get_username() is None
    assert steam.get_login_method() is None
    assert not steam.has_credentials()


def test_login_method_infers_password_for_legacy(monkeypatch):
    keyring = FakeKeyring()
    monkeypatch.setattr(steam, "_keyring", keyring)
    keyring.set_password("forager", "steam_username", "alice")
    keyring.set_password("forager", "steam_password", "hunter2")
    assert steam.get_login_method() == "password"


def test_qr_success_regex():
    m = steam._QR_SUCCESS_RE.search(
        "Success! Next time you can login with -username alice -remember-password instead of -qr."
    )
    assert m is not None
    assert m.group(1) == "alice"


def test_parse_qr_art():
    art = [
        "\u2588\u2588  \u2588\u2588",
        "    \u2588\u2588",
        "\u2588\u2588\u2588\u2588\u2588\u2588",
    ]
    grid = steam.parse_qr_art(art)
    assert grid == [
        [True, False, True],
        [False, False, True],
        [True, True, True],
    ]


def test_is_qr_art_line():
    assert steam._is_qr_art_line("  \u2588\u2588  ")
    assert steam._is_qr_art_line("\u2588\u2588\u2588\u2588")
    assert not steam._is_qr_art_line("The QR code has changed:")
    assert not steam._is_qr_art_line("")


def test_login_with_qr_parses_account(monkeypatch):
    captured = []

    def fake_run_dd(cmd, timeout, cancel_event=None, on_line=None):
        lines = [
            "Connecting to Steam3...",
            " Done!",
            "Logging in with QR code...",
            "Use the Steam Mobile App to sign in with this QR code:",
            "\u2588\u2588  \u2588\u2588",
            "\u2588\u2588\u2588\u2588\u2588\u2588",
            "The QR code has changed:",
            "\u2588\u2588\u2588\u2588  ",
            "\u2588\u2588\u2588\u2588\u2588\u2588",
            "Success! Next time you can login with -username alice -remember-password instead of -qr.",
            "Connecting to Steam3...",
            " Done!",
            "Got 4 licenses for account!",
        ]
        for line in lines:
            if on_line is not None:
                on_line(line)
        return [], "", 0, False

    monkeypatch.setattr(steam, "_run_dd", fake_run_dd)
    ok, detail = steam.login_with_qr(captured.append)
    assert ok and detail == "alice"
    assert len(captured) == 2
    assert steam.parse_qr_art(captured[0]) == [[True, False, True], [True, True, True]]
    assert steam.parse_qr_art(captured[1]) == [[True, True, False], [True, True, True]]


def test_login_with_qr_cancel(monkeypatch):
    monkeypatch.setattr(
        steam, "_run_dd", lambda cmd, timeout, cancel_event=None, on_line=None: ([], "", 0, True)
    )
    ok, detail = steam.login_with_qr(lambda _: None)
    assert not ok and detail == "Sign-in cancelled"


def test_verify_session_reuses_token(monkeypatch):
    calls = {}

    def fake_run_dd(cmd, timeout, cancel_event=None, on_line=None):
        calls["cmd"] = cmd
        return ["Connecting to Steam3...", " Done!", "Got 3 licenses for account!"], "", 0, False

    monkeypatch.setattr(steam, "_run_dd", fake_run_dd)
    ok, detail = steam.verify_session("alice")
    assert ok and detail == "Signed in as alice"
    assert calls["cmd"][calls["cmd"].index("-username") + 1] == "alice"
    assert "-password" not in calls["cmd"]


def test_verify_session_rejected_token(monkeypatch):
    monkeypatch.setattr(
        steam, "_run_dd",
        lambda cmd, timeout, cancel_event=None, on_line=None: (
            ["Connecting to Steam3...", "Done!", "Access token was rejected (Expired).",
             "Unable to get steam3 credentials."], "", 1, False,
        ),
    )
    ok, detail = steam.verify_session("alice")
    assert not ok and "rejected" in detail


def test_verify_session_no_stored_token(monkeypatch):
    monkeypatch.setattr(
        steam, "_run_dd",
        lambda cmd, timeout, cancel_event=None, on_line=None: (
            [], 'Enter account password for "alice": ', 1, False,
        ),
    )
    ok, detail = steam.verify_session("alice")
    assert not ok and "sign in again" in detail
