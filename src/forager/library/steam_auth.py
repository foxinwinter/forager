"""Native Steam sign-in via Valve's IAuthenticationService (no webview).

Replaces the QtWebEngine login dialog: Steam's login page polls auth sessions
over a WebSocket that hangs in QtWebEngine, so instead we talk to Steam's own
JSON/Web API directly with the standard library only:

- QR sign-in (mobile app): ``BeginAuthSessionViaQR`` -> ``PollAuthSessionStatus``
- username/password + Steam Guard: ``GetPasswordRSAPublicKey`` ->
  ``BeginAuthSessionViaCredentials`` -> ``UpdateAuthSessionWithSteamGuardCode`` ->
  ``PollAuthSessionStatus``
- web session cookie: ``login.steampowered.com/jwt/finalizelogin`` plus the
  returned ``transfer_info`` ``/settoken`` POSTs, yielding the
  ``steamLoginSecure`` cookie value.

Live-verified 2026-08-01 against the real endpoints:
- ``BeginAuthSessionViaQR`` takes a JSON body (``device_details``); the poll and
  guard-code endpoints take form-encoded bodies; ``GetPasswordRSAPublicKey`` is
  GET-only (POST -> HTTP 405).
- A rejected Steam Guard code is silently accepted (``{"response":{}}``) and
  only surfaces on the next poll as ``had_remote_interaction: false`` with no
  tokens.
- A bogus ``BeginAuthSessionViaCredentials`` returns ``{"response":{}}`` (empty
  response = invalid account name or password).
- ``finalizelogin`` returns JSON; a bad nonce -> ``{"success": false, ...}``.
"""
from __future__ import annotations

import base64
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

API_BASE = "https://api.steampowered.com"
LOGIN_URL = "https://login.steampowered.com"
COMMUNITY_URL = "https://steamcommunity.com/"
FINALIZE_URL = LOGIN_URL + "/jwt/finalizelogin"
BEGIN_QR_URL = API_BASE + "/IAuthenticationService/BeginAuthSessionViaQR/v1"
BEGIN_CREDENTIALS_URL = API_BASE + "/IAuthenticationService/BeginAuthSessionViaCredentials/v1"
POLL_URL = API_BASE + "/IAuthenticationService/PollAuthSessionStatus/v1/"
GUARD_CODE_URL = API_BASE + "/IAuthenticationService/UpdateAuthSessionWithSteamGuardCode/v1/"
RSA_KEY_URL = API_BASE + "/IAuthenticationService/GetPasswordRSAPublicKey/v1/"

USER_AGENT = "forager"

_PLATFORM_WEB = 2
_OS_TYPE = 20

# Steam Guard confirmation types (EAuthSessionGuardType).
GUARD_EMAIL_CODE = 2
GUARD_DEVICE_CODE = 3
GUARD_DEVICE_CONFIRMATION = 4
GUARD_EMAIL_CONFIRMATION = 5

_ORIGIN_HEADERS = {
    "Origin": "https://steamcommunity.com",
    "Referer": "https://steamcommunity.com/",
}

_GUARD_CODE_TYPES = (GUARD_EMAIL_CODE, GUARD_DEVICE_CODE)


class SteamAuthError(Exception):
    """A Steam auth API call failed (HTTP error, rejected login, etc.)."""

    def __init__(self, message: str, status: int | None = None, detail=None):
        super().__init__(message)
        self.status = status
        self.detail = detail


@dataclass
class AuthSession:
    """A started (but not yet authorized) auth session."""

    client_id: str
    request_id: str
    interval: float = 5.0
    challenge_url: str | None = None
    steamid: str | None = None
    allowed_confirmations: list[dict] = field(default_factory=list)

    @property
    def code_types(self) -> list[int]:
        """Guard code types the session will accept (2=email, 3=app)."""
        return [
            int(c.get("confirmation_type"))
            for c in self.allowed_confirmations
            if int(c.get("confirmation_type", 0)) in _GUARD_CODE_TYPES
        ]

    @property
    def requires_code(self) -> bool:
        return bool(self.code_types)

    @property
    def needs_approval(self) -> bool:
        return any(
            int(c.get("confirmation_type", 0)) in (GUARD_DEVICE_CONFIRMATION, GUARD_EMAIL_CONFIRMATION)
            for c in self.allowed_confirmations
        )


@dataclass
class PollResult:
    """Outcome of one ``PollAuthSessionStatus`` call."""

    expired: bool = False
    had_remote_interaction: bool = False
    refresh_token: str | None = None
    access_token: str | None = None
    account_name: str | None = None
    new_client_id: str | None = None

    @property
    def authorized(self) -> bool:
        return bool(self.refresh_token)


# --------------------------------------------------------------------------
# HTTP helpers (single seam for tests to monkeypatch)
# --------------------------------------------------------------------------


def _urlopen(request: urllib.request.Request, timeout: float = 30.0):
    return urllib.request.urlopen(request, timeout=timeout)


def _open_with_cookies(request: urllib.request.Request, jar: http.cookiejar.CookieJar, timeout: float = 30.0):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return opener.open(request, timeout=timeout)


def _make_request(url: str, method: str, data: bytes | None = None, headers: dict | None = None):
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    return urllib.request.Request(url, data=data, headers=h, method=method)


def _status(resp) -> int:
    status = getattr(resp, "status", None)
    if status is None and hasattr(resp, "getcode"):
        status = resp.getcode()
    return status if status is not None else 200


def _read_text(resp) -> str:
    raw = resp.read()
    if isinstance(raw, bytes):
        return raw.decode("utf-8", "replace")
    return str(raw)


def _response_dict(text: str, status: int = 200) -> dict:
    try:
        data = json.loads(text)
    except Exception:
        data = {}
    resp = data.get("response") if isinstance(data, dict) else None
    if not isinstance(resp, dict):
        return {}
    if resp.get("error_code") or resp.get("error_message"):
        raise SteamAuthError(
            resp.get("error_message") or f"Steam error {resp.get('error_code')}",
            status=status,
            detail=resp,
        )
    if resp.get("captcha_needed"):
        raise SteamAuthError(
            "Steam is asking for a CAPTCHA — try the QR sign-in instead.",
            status=status,
            detail=resp,
        )
    return resp


def _post(url: str, body: bytes, timeout: float, headers: dict | None = None) -> tuple[int, str]:
    req = _make_request(url, "POST", body, headers)
    try:
        resp = _urlopen(req, timeout)
        status = _status(resp)
        text = _read_text(resp)
    except urllib.error.HTTPError as e:
        raise SteamAuthError("Steam returned an error response", status=e.code, detail=_read_text(e))
    return status, text


def _get(url: str, params: dict, timeout: float) -> tuple[int, str]:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = _make_request(url, "GET")
    try:
        resp = _urlopen(req, timeout)
        return _status(resp), _read_text(resp)
    except urllib.error.HTTPError as e:
        raise SteamAuthError("Steam returned an error response", status=e.code, detail=_read_text(e))


def _json_body(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _form_body(fields: dict) -> bytes:
    return urllib.parse.urlencode(fields).encode("utf-8")


def _cookie_value(jar: http.cookiejar.CookieJar, name: str) -> str | None:
    for cookie in jar:
        if cookie.name == name:
            return cookie.value
    return None


# --------------------------------------------------------------------------
# QR sign-in
# --------------------------------------------------------------------------


def start_qr_session(device_friendly_name: str = "forager", timeout: float = 30.0) -> AuthSession:
    """Begin a QR sign-in session. ``challenge_url`` is what the QR encodes."""
    payload = {
        "device_details": {
            "device_friendly_name": device_friendly_name,
            "platform_type": _PLATFORM_WEB,
            "os_type": _OS_TYPE,
        }
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        **_ORIGIN_HEADERS,
    }
    status, text = _post(BEGIN_QR_URL, _json_body(payload), timeout, headers)
    resp = _response_dict(text, status)
    return AuthSession(
        client_id=resp.get("client_id") or "",
        request_id=resp.get("request_id") or "",
        interval=float(resp.get("interval") or 5),
        challenge_url=resp.get("challenge_url"),
        allowed_confirmations=_confirmations(resp),
    )


def _confirmations(resp: dict) -> list[dict]:
    allowed = resp.get("allowed_confirmations")
    if not isinstance(allowed, list):
        return []
    return [c for c in allowed if isinstance(c, dict)]


def poll_session(client_id: str, request_id: str, timeout: float = 30.0) -> PollResult:
    """Poll a session's status. A 404 means the session expired (QR rotated out)."""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        **_ORIGIN_HEADERS,
    }
    try:
        status, text = _post(POLL_URL, _form_body({"client_id": client_id, "request_id": request_id}), timeout, headers)
    except SteamAuthError as e:
        if e.status == 404:
            return PollResult(expired=True)
        raise
    resp = _response_dict(text, status)
    return PollResult(
        had_remote_interaction=bool(resp.get("had_remote_interaction")),
        refresh_token=resp.get("refresh_token") or None,
        access_token=resp.get("access_token") or None,
        account_name=resp.get("account_name") or None,
        new_client_id=resp.get("new_client_id") or None,
    )


def update_session_with_guard_code(
    client_id: str,
    code: str,
    code_type: int,
    steamid: str | None = None,
    timeout: float = 30.0,
) -> None:
    """Submit an email (2) or authenticator (3) Steam Guard code.

    Steam silently accepts a wrong code (``{"response":{}}``); a rejected code
    only shows up on the next ``poll_session`` (no tokens, no interaction).
    """
    fields = {"client_id": client_id, "code": code, "code_type": str(code_type)}
    if steamid:
        fields["steamid"] = steamid
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        **_ORIGIN_HEADERS,
    }
    status, text = _post(GUARD_CODE_URL, _form_body(fields), timeout, headers)
    _response_dict(text, status)


# --------------------------------------------------------------------------
# Username / password sign-in
# --------------------------------------------------------------------------


def _fetch_rsa_key(account_name: str, timeout: float = 30.0) -> dict | None:
    status, text = _get(RSA_KEY_URL, {"account_name": account_name}, timeout)
    resp = _response_dict(text, status)
    if "publickey_mod" not in resp or "publickey_exp" not in resp or "timestamp" not in resp:
        return None
    try:
        return {
            "mod": int(resp["publickey_mod"], 16),
            "exp": int(resp["publickey_exp"], 16),
            "timestamp": int(resp["timestamp"]),
        }
    except (TypeError, ValueError):
        return None


def _encrypt_password(password: str, mod: int, exp: int) -> bytes:
    """PKCS#1 v1.5 (type 2) RSA encrypt of the password with Steam's key."""
    data = password.encode("utf-8")
    size = (mod.bit_length() + 7) // 8
    if len(data) > size - 11:
        raise SteamAuthError("password too long for Steam's RSA key")
    pad_len = size - len(data) - 3
    pad = bytearray(pad_len)
    while True:
        pad[:] = os.urandom(pad_len)
        if b"\x00" not in pad:
            break
    padded = b"\x00\x02" + bytes(pad) + b"\x00" + data
    cipher = pow(int.from_bytes(padded, "big"), exp, mod)
    return cipher.to_bytes(size, "big")


def start_credentials_session(
    username: str,
    password: str,
    device_friendly_name: str = "forager",
    timeout: float = 30.0,
) -> AuthSession:
    """Begin a username/password session; a Steam Guard code may follow."""
    rsa = _fetch_rsa_key(username, timeout)
    if not rsa:
        raise SteamAuthError("Could not load Steam's encryption key for this account.")
    encrypted = base64.b64encode(_encrypt_password(password, rsa["mod"], rsa["exp"])).decode("ascii")
    fields = {
        "persistence": "1",
        "encrypted_password": encrypted,
        "account_name": username,
        "encryption_timestamp": str(rsa["timestamp"]),
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        **_ORIGIN_HEADERS,
    }
    status, text = _post(BEGIN_CREDENTIALS_URL, _form_body(fields), timeout, headers)
    resp = _response_dict(text, status)
    if not resp:
        raise SteamAuthError("Invalid account name or password.", status=status)
    steamid = resp.get("steamid")
    return AuthSession(
        client_id=resp.get("client_id") or "",
        request_id=resp.get("request_id") or "",
        interval=float(resp.get("interval") or 5),
        steamid=str(steamid) if steamid else None,
        allowed_confirmations=_confirmations(resp),
    )


# --------------------------------------------------------------------------
# Web session (steamLoginSecure cookie)
# --------------------------------------------------------------------------


def steamid_from_refresh_token(refresh_token: str) -> str | None:
    """Read the account's SteamID64 out of the refresh token's JWT payload."""
    try:
        payload = refresh_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None
    sub = data.get("sub")
    return str(sub) if sub else None


def finalize_login(refresh_token: str, steamid: str | None = None, timeout: float = 30.0) -> str:
    """Exchange the refresh token for the ``steamLoginSecure`` cookie value.

    Returns the cookie's value (``<steamid>||<digest>``).
    """
    jar = http.cookiejar.CookieJar()
    session_id = _fetch_session_id(jar, timeout)
    if not session_id:
        raise SteamAuthError("Could not obtain a Steam session id.")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        **_ORIGIN_HEADERS,
    }
    body = _form_body({
        "nonce": refresh_token,
        "sessionid": session_id,
        "redir": "https://steamcommunity.com/login/home/?goto=",
    })
    req = _make_request(FINALIZE_URL, "POST", body, headers)
    try:
        resp = _open_with_cookies(req, jar, timeout)
        status = _status(resp)
        text = _read_text(resp)
    except urllib.error.HTTPError as e:
        raise SteamAuthError("Steam rejected the login finalization.", status=e.code, detail=_read_text(e))
    try:
        data = json.loads(text) if text else {}
    except Exception:
        data = {}

    if data.get("success") is False or not data.get("transfer_info"):
        raise SteamAuthError("Steam rejected the login finalization.", status=status, detail=data)

    account_id = str(data.get("steamID") or steamid or "")
    for transfer in data.get("transfer_info") or []:
        url = transfer.get("url") if isinstance(transfer, dict) else None
        if not url:
            continue
        params = dict(transfer.get("params") or {})
        if account_id:
            params["steamID"] = account_id
        req = _make_request(url, "POST", _form_body(params), headers)
        try:
            _open_with_cookies(req, jar, timeout).read()
        except urllib.error.HTTPError as e:
            raise SteamAuthError(f"Steam cookie transfer failed ({url}).", status=e.code, detail=_read_text(e))

    cookie = _cookie_value(jar, "steamLoginSecure")
    if not cookie:
        raise SteamAuthError("Steam did not return a login cookie.")
    return cookie


def _fetch_session_id(jar: http.cookiejar.CookieJar, timeout: float) -> str | None:
    req = _make_request(COMMUNITY_URL, "POST", data=b"", headers=_ORIGIN_HEADERS)
    try:
        _open_with_cookies(req, jar, timeout).read()
    except urllib.error.HTTPError as e:
        raise SteamAuthError("Could not reach Steam Community.", status=e.code, detail=_read_text(e))
    return _cookie_value(jar, "sessionid")
