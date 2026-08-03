"""Subprocess helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path


def run_checked(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> str:
    """Run *cmd* capturing combined output; raise on non-zero exit.

    Returns the combined stdout+stderr of the command.
    """
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
    return (proc.stdout or "") + (proc.stderr or "")
