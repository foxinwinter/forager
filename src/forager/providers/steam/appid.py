"""Steam App ID resolution by name.

Given a ``Game`` that is not installed through Steam, guess its Steam App ID
so CDN art can be fetched for it. Only confident (exact or distinctive-prefix)
store-title matches are accepted, so ambiguous folder names can never pull in
a wrong game. Results are cached on disk per search term.
"""
from __future__ import annotations
import json
import re
import threading
import urllib.parse
import urllib.request

from forager.core.game import Game
from forager.artwork.cache import art_cache_dir

STEAM_STORE_SEARCH = "https://store.steampowered.com/api/storesearch/?term={term}&l=english&cc=US"

_STEAM_APPID_CACHE: dict[str, str] = {}
_STEAM_APPID_LOCK = threading.Lock()
_STEAM_APPID_FILE = art_cache_dir() / "steam_app_ids.json"
_STEAM_APPID_KEY_PREFIX = "v2:"


def _appid_cache() -> dict[str, str]:
    global _STEAM_APPID_CACHE
    if not _STEAM_APPID_CACHE:
        try:
            _STEAM_APPID_CACHE = json.loads(_STEAM_APPID_FILE.read_text("utf-8"))
        except Exception:
            _STEAM_APPID_CACHE = {}
    return _STEAM_APPID_CACHE


def _cache_appid(term: str, app_id: str | None) -> None:
    cache = _appid_cache()
    cache[_STEAM_APPID_KEY_PREFIX + term.lower()] = app_id or ""
    try:
        _STEAM_APPID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STEAM_APPID_FILE.write_text(json.dumps(cache))
    except Exception:
        pass


def _steam_search_terms(game: Game) -> list[str] | None:
    """Candidate Steam store search terms, most specific first.

    ``search_names`` wins outright. Series games search their holding folder
    plus the game name before falling back to the bare name; every game keeps
    the bare (leaf) name as a last resort.
    """
    if game.search_names:
        return list(game.search_names)
    terms: list[str] = []
    plan = game.sgdb_search
    if plan:
        queries, match_term = plan
        if match_term:
            terms = [f"{q} {match_term}" for q in queries] + [match_term]
        else:
            terms = list(queries)
    name = game.name
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    leaf = name.strip()
    if leaf and (not terms or leaf != terms[-1]):
        terms.append(leaf)
    return terms or None


def _name_matches(store_name: str, term: str) -> bool:
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    n = norm(store_name)
    t = norm(term)
    if n == t:
        return True
    if len(t) >= 8 and n.startswith(t) and (len(n) == len(t) or n[len(t)] == " "):
        return True
    return False


def _steam_store_search(term: str) -> str | None:
    url = STEAM_STORE_SEARCH.format(term=urllib.parse.quote(term))
    req = urllib.request.Request(url, headers={"User-Agent": "forager/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    for it in payload.get("items") or []:
        if it.get("type") == "app" and _name_matches(it.get("name") or "", term):
            return str(it.get("id"))
    return None


def steam_app_id(game: Game) -> str | None:
    """Resolve the Steam App ID for a game.

    Steam games use their own ``app_id``. Every other game is looked up on the
    Steam store by name, accepting only confident (exact or distinctive-prefix)
    title matches. Lookups are cached on disk per search term.
    """
    if game.app_id:
        return game.app_id
    terms = _steam_search_terms(game)
    if not terms:
        return None
    with _STEAM_APPID_LOCK:
        cache = _appid_cache()
        for term in terms:
            key = _STEAM_APPID_KEY_PREFIX + term.lower()
            if key not in cache:
                cache[key] = _steam_store_search(term) or ""
                _cache_appid(term, cache[key])
            if cache[key]:
                return cache[key]
    return None
