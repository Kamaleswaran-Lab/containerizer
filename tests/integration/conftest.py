from __future__ import annotations

import os
import subprocess
import pytest
from pathlib import Path

from sandbox.profiles import get_profile


def _find_image() -> str:
    """Locate a .sif image for testing."""
    profile = get_profile()
    image = os.path.join(profile.image_dir, "base-agent.sif")
    if os.path.exists(image):
        return image
    # Fallback: look in definitions/
    repo_root = Path(__file__).parent.parent.parent
    local = repo_root / "definitions" / "base-agent.sif"
    if local.exists():
        return str(local)
    pytest.skip("No .sif image available for integration tests")


@pytest.fixture(scope="session")
def sif_image() -> str:
    return _find_image()


@pytest.fixture
def input_dir(tmp_path: Path) -> Path:
    d = tmp_path / "input"
    d.mkdir()
    (d / "data.txt").write_text("test input data")
    (d / "config.json").write_text('{"key": "value"}')
    return d


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


def run_in_container(
    sif_image: str,
    command: str,
    binds: list[str] | None = None,
    env_vars: dict[str, str] | None = None,
    extra_flags: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Helper to run a command inside the container."""
    cmd = ["apptainer", "exec", "--containall", "--cleanenv"]
    cmd.extend(["--bind", "/etc/resolv.conf:/etc/resolv.conf:ro"])

    for bind in (binds or []):
        cmd.extend(["--bind", bind])

    for k, v in (env_vars or {}).items():
        cmd.extend(["--env", f"{k}={v}"])

    for flag in (extra_flags or []):
        cmd.append(flag)

    cmd.append(sif_image)
    cmd.extend(["bash", "-c", command])

    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
