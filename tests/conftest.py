from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_input_dir(tmp_path: Path) -> Path:
    d = tmp_path / "input"
    d.mkdir()
    (d / "sample.txt").write_text("test data")
    return d


@pytest.fixture
def minimal_config(tmp_input_dir: Path) -> dict:
    return {
        "task_id": "test-task",
        "image": "base-agent.sif",
        "mounts": {
            "inputs": [
                {"src": str(tmp_input_dir), "dest": "/input/data"}
            ]
        },
        "resources": {
            "cpus": 2,
            "mem_gb": 8,
            "time": "01:00:00",
            "gpu": 0,
            "partition": "general",
        },
        "network": True,
        "entrypoint": "claude",
    }
