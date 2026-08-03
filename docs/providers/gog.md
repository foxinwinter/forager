# GOG provider (design notes — placeholder)

Package: `src/forager/providers/gog/` (empty, nothing wired up yet).

## Plan

Backend: GOG's **unofficial web API** for the owned library of offline
installers:

- **auth** — GOG web login (username/password + a `GOGCOM` token / refresh
  token stored via the system keyring, mirroring the Steam account store).
- **ownership** — `GET /users/<userid>/owned` for owned games and their
  installers.
- **download** — direct-installer URLs require a session token; download
  progress maps onto the existing downloads page.
- **launch** — offline installers extract to a per-game folder and launch via
  `library/launcher.py` like any standalone game.

Status: **planned** (roadmap item 6).
