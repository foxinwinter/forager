# Torrent backend (design notes — placeholder)

Package: `src/forager/providers/torrent/` (empty, nothing wired up yet).

## Plan

Backend: **`libtorrent`** (via `python-libtorrent` / `libtorrent-python`) as a
generic downloader, in addition to Steam/EGS/GOG downloads.

- The user provides a `.torrent` file or a magnet link; a torrenting provider
  exposes the download with the same progress surface the downloads page
  already renders.
- DHT / tracker state kept under the cache dir; per-download progress
  (`DownloadProgress`-shaped) streamed to the downloads page.

## Legal note

Legality of torrented content is entirely the user's responsibility — forager
does not search, index or rate torrent sites.

Status: **planned** (roadmap item 8).
