"""Steam game downloads (roadmap item 3).

Planned: DepotDownloader already vendored for Steam login (see
``forager.providers.steam.account``) and reused for Proton installs (see
``forager.compatibility.proton``); the download page
(``forager.ui.pages.downloads``) already renders progress. The remaining work
is driving appid/depot downloads for owned titles from the stored credentials.

Nothing is implemented yet.
"""
from __future__ import annotations


def download_app(app_id: str, destination: str) -> None:
    """Download a Steam app (placeholder).

    Raises ``NotImplementedError`` until game downloads land (roadmap item 3).
    """
    raise NotImplementedError("Steam game downloads are planned (roadmap item 3)")
