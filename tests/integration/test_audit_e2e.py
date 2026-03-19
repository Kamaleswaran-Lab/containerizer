from __future__ import annotations

import hashlib
import json

import pytest
from pathlib import Path

from sandbox.audit import generate_manifest, generate_metadata
from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class TestAuditEndToEnd:
    def test_manifest_after_run(self, sif_image: str, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        logs_dir = tmp_path / "logs"

        run_in_container(
            sif_image,
            "echo 'file1' > /output/a.txt && echo 'file2' > /output/b.txt",
            binds=[f"{output_dir}:/output:rw"],
        )

        generate_manifest(str(output_dir), str(logs_dir))
        manifest = (logs_dir / "manifest.txt").read_text()
        assert "a.txt" in manifest
        assert "b.txt" in manifest

    def test_manifest_checksums_correct(self, sif_image: str, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        logs_dir = tmp_path / "logs"

        run_in_container(
            sif_image,
            "echo 'checksum-test' > /output/check.txt",
            binds=[f"{output_dir}:/output:rw"],
        )

        generate_manifest(str(output_dir), str(logs_dir))
        manifest = (logs_dir / "manifest.txt").read_text()

        expected_hash = _hash_file(output_dir / "check.txt")
        assert expected_hash in manifest

    def test_metadata_structure(self, tmp_path: Path) -> None:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        generate_metadata(
            str(logs_dir),
            task_id="test-audit-001",
            exit_code=0,
            image="base-agent.sif",
            start_time="2026-03-18T00:00:00+00:00",
        )
        meta = json.loads((logs_dir / "meta.json").read_text())
        assert meta["task_id"] == "test-audit-001"
        assert meta["exit_code"] == 0
        assert meta["image"] == "base-agent.sif"
        assert "node" in meta
        assert "start_time" in meta
        assert "end_time" in meta
