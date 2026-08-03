"""Filesystem helpers."""
from __future__ import annotations
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) if missing; return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
