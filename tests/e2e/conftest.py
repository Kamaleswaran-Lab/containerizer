from __future__ import annotations

import getpass
import os
import shutil
import subprocess
import uuid

import pytest
import yaml

from sandbox.profiles import get_profile


def _find_image(name: str = "base-agent.sif") -> str:
    """Locate a .sif image for testing."""
    from pathlib import Path

    profile = get_profile()
    image = os.path.join(profile.image_dir, name)
    if os.path.exists(image):
        return image
    group_path = Path("/hpc/group/kamaleswaranlab/.images/containerizer") / name
    if group_path.exists():
        return str(group_path)
    repo_root = Path(__file__).parent.parent.parent
    local = repo_root / "images" / name
    if local.exists():
        return str(local)
    legacy = repo_root / "definitions" / name
    if legacy.exists():
        return str(legacy)
    pytest.skip(f"No {name} image available for E2E tests")


@pytest.fixture(scope="session")
def sif_image() -> str:
    return _find_image("base-agent.sif")


@pytest.fixture(autouse=True)
def skip_no_srun():
    """Skip all E2E tests if srun is not available."""
    if shutil.which("srun") is None:
        pytest.skip("srun not available — cannot run E2E SLURM tests")


def _shared_tmp_base() -> str:
    """Return a shared-filesystem temp base visible to compute nodes."""
    profile = get_profile()
    base = os.path.join(profile.scratch_base, "sandbox", "e2e-tmp")
    os.makedirs(base, exist_ok=True)
    return base


@pytest.fixture
def e2e_scratch():
    """Create a unique temp dir on the shared filesystem, cleaned up after test."""
    base = _shared_tmp_base()
    unique = f"e2e-{uuid.uuid4().hex[:8]}"
    path = os.path.join(base, unique)
    os.makedirs(path, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def e2e_output_dir(e2e_scratch):
    """Output directory on shared filesystem."""
    d = os.path.join(e2e_scratch, "output")
    os.makedirs(d, exist_ok=True)
    return d


@pytest.fixture
def e2e_task_config(e2e_scratch, sif_image):
    """Write a minimal task YAML and return its path."""
    task_yaml = os.path.join(e2e_scratch, "task.yaml")
    config = {
        "task_id": "e2e-test",
        "image": os.path.basename(sif_image),
        "resources": {
            "partition": "scavenger",
            "time": "00:05:00",
            "cpus": 1,
            "mem_gb": 4,
        },
        "entrypoint": "bash",
    }
    with open(task_yaml, "w") as f:
        yaml.dump(config, f)
    return task_yaml
