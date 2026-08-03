# forager documentation

Index of the project documentation.

## Overview

- [Architecture](architecture.md) — high-level overview of the codebase
- [Roadmap](roadmap.md) — the plan towards `v1.0.0`

## Guides

- [Build](build.md) — development, build and release guide
- [Contributing](contributing.md) — coding standards & contribution guide
- [Changelog](changelog.md) — release history

## Architecture deep-dives

- [Startup sequence](architecture/startup.md)
- [Game discovery & library pipeline](architecture/library.md)
- [Game launch lifecycle](architecture/launcher.md)
- [Artwork generation & cache pipeline](architecture/artwork.md)
- [Provider abstraction](architecture/providers.md)
- [Window/page/widget hierarchy](architecture/ui.md)
- [Worker threads, signals & cancellation](architecture/threading.md)
- [Config/cache/data directory layout](architecture/filesystem.md)
- [Settings lifecycle & persistence](architecture/settings.md)

## Providers & services

- [Steam implementation](providers/steam.md)
- [Epic Games design notes](providers/epic.md) (placeholder)
- [GOG design notes](providers/gog.md) (placeholder)
- [Torrent backend notes](providers/torrent.md) (placeholder)
- [SteamGridDB integration](services/steamgriddb.md)
- [Steam Web API usage](services/steam_web_api.md)

## Development

- [Project layout](development/project_layout.md) — every package explained
- [Coding style](development/coding_style.md) — formatting, naming, typing
- [Testing](development/testing.md) — pytest & Qt testing
- [Caching](development/caching.md) — artwork/metadata cache behavior
- [Packaging](development/packaging.md) — packaging & release process
- [Dependencies](development/dependencies.md) — third-party libraries & rationale

## Design

- [UI/UX guidelines](design/ui_guidelines.md)
- [Typography](design/typography.md)
- [Theming](design/theming.md)
- [Navigation](design/navigation.md)
- [Screenshots](design/screenshots/)

## API references

- [Game dataclass](api/game.md)
- [Settings API](api/config.md)
- [Launcher interfaces](api/launcher.md)
- [Artwork pipeline API](api/artwork.md)

## Diagrams (Mermaid)

- [Startup flowchart](diagrams/startup.mmd)
- [Artwork pipeline](diagrams/artwork_pipeline.mmd)
- [Launch sequence](diagrams/launcher_flow.mmd)
- [Package relationships](diagrams/project_layout.mmd)
