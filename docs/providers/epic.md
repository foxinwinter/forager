# Epic Games provider (design notes — placeholder)

Package: `src/forager/providers/epic/` (empty, nothing wired up yet).

## Plan

Backend: **Legendary**, the open-source Epic Games Store CLI. It provides all
three provider responsibilities out of the box:

- **auth** — `legendary auth` (device-code login), stored in its own config;
- **download** — `legendary download <app>` with progress;
- **launch** — `legendary launch <app>`.

## Integration sketch

- A new `providers/epic/provider.py` module implementing the same surface as
  `providers/steam` (ownership list, download, launch) so the library grid and
  downloads page can treat Epic titles like any other.
- Locate the Legendary binary and config dir; fall back to the distro package
  (`legendary`).
- Progress lines from `legendary download` mapped onto the existing
  `DownloadProgress` dataclass in `compatibility/proton.py` and the downloads
  page.

Status: **planned** (roadmap item 5).
