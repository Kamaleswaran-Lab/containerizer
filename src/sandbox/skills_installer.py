"""Install sandbox skills into agent platform directories."""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path

# Skills to install and their source paths within the package
SKILL_FILES = {
    "sandbox-install": "sandbox-install/SKILL.md",
    "sandbox-configure": "sandbox-configure/SKILL.md",
    "sandbox-reference": "sandbox-reference/SKILL.md",
}

REFERENCE_FILES = {
    "references/template.yaml": "sandbox-configure/references/template.yaml",
}

PLATFORMS = ("claude", "cursor", "gemini", "generic")


def detect_platform(cwd: Path | None = None, home: Path | None = None) -> str:
    """Auto-detect agent platform from directory markers.

    Checks cwd first, then falls back to home directory.
    """
    cwd = cwd or Path.cwd()
    home = home or Path.home()

    # Check cwd first — most specific signal
    if (cwd / ".claude").is_dir():
        return "claude"
    if (cwd / ".cursor").is_dir():
        return "cursor"
    if (cwd / ".gemini").is_dir():
        return "gemini"

    # Fall back to home directory markers
    if (home / ".claude").is_dir():
        return "claude"
    if (home / ".gemini").is_dir():
        return "gemini"

    return "generic"


def get_target_dir(platform: str, global_install: bool = False) -> Path:
    """Return the target directory for skill installation."""
    cwd = Path.cwd()
    home = Path.home()

    if platform == "claude":
        if global_install:
            return home / ".claude" / "commands"
        return cwd / ".claude" / "commands"
    elif platform == "cursor":
        if global_install:
            return home / ".cursor" / "rules"
        return cwd / ".cursor" / "rules"
    elif platform == "gemini":
        if global_install:
            return home / ".gemini"
        return cwd / ".gemini"
    else:
        return cwd / "skills"


def get_skills_package_path() -> Path:
    """Return the path to the bundled skills directory."""
    return Path(str(importlib.resources.files("sandbox.skills")))


def install_skills(platform: str, global_install: bool = False) -> list[Path]:
    """Copy skill files to the target platform directory. Returns list of installed paths."""
    target_dir = get_target_dir(platform, global_install)
    skills_dir = get_skills_package_path()
    installed: list[Path] = []

    # Install main skill files (SKILL.md -> sandbox-<name>.md)
    for name, src_rel in SKILL_FILES.items():
        src = skills_dir / src_rel
        dest = target_dir / f"{name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        installed.append(dest)

    # Install reference files
    for dest_rel, src_rel in REFERENCE_FILES.items():
        src = skills_dir / src_rel
        dest = target_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        installed.append(dest)

    return installed
