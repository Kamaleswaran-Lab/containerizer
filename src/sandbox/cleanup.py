from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import click

from sandbox.profiles import get_profile


def find_task_dirs(older_than_seconds: int | None = None) -> list[Path]:
    """List all task directories, optionally filtered by age."""
    profile = get_profile()
    tasks_root = Path(profile.tasks_dir)
    if not tasks_root.exists():
        return []

    dirs = sorted(tasks_root.iterdir())
    if older_than_seconds is None:
        return dirs

    cutoff = time.time() - older_than_seconds
    return [d for d in dirs if d.stat().st_mtime < cutoff]


def remove_task(task_dir: Path) -> None:
    """Remove a task directory and all its contents."""
    shutil.rmtree(task_dir)


def parse_duration(duration_str: str) -> int:
    """Parse a duration string like '7d', '24h', '30m' to seconds."""
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    suffix = duration_str[-1].lower()
    if suffix not in units:
        raise click.BadParameter(f"Unknown duration unit: {suffix}. Use d/h/m/s.")
    return int(duration_str[:-1]) * units[suffix]
