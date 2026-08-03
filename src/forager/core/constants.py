"""Application-wide constants.

Central place for names and versions so modules (keyring services, user-agent
strings, display names) never drift apart.
"""
from __future__ import annotations

APP_NAME = "forager"
ORG_NAME = "forager"
VERSION = "0.2.0"

# Keyring service used by the Steam account store and the SteamGridDB token
# store (see forager.providers.steam.account and forager.services.steamgriddb).
KEYRING_SERVICE = APP_NAME

# Relative name of the packaged data directory (fonts, icons) inside the
# installed package — kept in sync with forager.core.paths.resources_dir.
ASSETS_DIRNAME = "assets"
