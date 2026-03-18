from __future__ import annotations

import json
import pytest
from pathlib import Path

from sandbox.audit import generate_manifest, generate_metadata


class TestManifest:
    def test_generates_manifest_file(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "result.txt").write_text("hello")
        (output_dir / "data.csv").write_text("a,b\n1,2")

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        generate_manifest(str(output_dir), str(logs_dir))

        manifest = (logs_dir / "manifest.txt").read_text()
        assert "result.txt" in manifest
        assert "data.csv" in manifest
        # SHA-256 hashes are 64 hex chars
        for line in manifest.strip().splitlines():
            hash_part = line.split("  ")[0]
            assert len(hash_part) == 64

    def test_empty_output_produces_empty_manifest(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        generate_manifest(str(output_dir), str(logs_dir))
        manifest = (logs_dir / "manifest.txt").read_text()
        assert manifest.strip() == ""


class TestMetadata:
    def test_generates_meta_json(self, tmp_path: Path) -> None:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        generate_metadata(
            logs_dir=str(logs_dir),
            task_id="test-task-20260318-120000",
            exit_code=0,
            image="base-agent.sif",
            start_time="2026-03-18T12:00:00+00:00",
        )

        meta = json.loads((logs_dir / "meta.json").read_text())
        assert meta["task_id"] == "test-task-20260318-120000"
        assert meta["exit_code"] == 0
        assert meta["start_time"] == "2026-03-18T12:00:00+00:00"
        assert "end_time" in meta
        assert "node" in meta
