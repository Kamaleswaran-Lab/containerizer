from __future__ import annotations

import os
import uuid

import pytest
from pathlib import Path

from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


class TestReadOnlyIsolation:
    def test_readonly_mount_blocks_write(self, sif_image: str, input_dir: Path) -> None:
        result = run_in_container(
            sif_image,
            "touch /input/new-file.txt",
            binds=[f"{input_dir}:/input:ro"],
        )
        assert result.returncode != 0
        assert not (input_dir / "new-file.txt").exists()

    def test_readonly_mount_blocks_delete(self, sif_image: str, input_dir: Path) -> None:
        result = run_in_container(
            sif_image,
            "rm /input/data.txt",
            binds=[f"{input_dir}:/input:ro"],
        )
        assert result.returncode != 0
        assert (input_dir / "data.txt").exists()

    def test_readonly_mount_allows_read(self, sif_image: str, input_dir: Path) -> None:
        result = run_in_container(
            sif_image,
            "cat /input/data.txt",
            binds=[f"{input_dir}:/input:ro"],
        )
        assert result.returncode == 0
        assert "test input data" in result.stdout


class TestWritableMount:
    def test_writable_mount_allows_write(self, sif_image: str, output_dir: Path) -> None:
        result = run_in_container(
            sif_image,
            "echo 'hello' > /output/result.txt",
            binds=[f"{output_dir}:/output:rw"],
        )
        assert result.returncode == 0
        assert (output_dir / "result.txt").read_text().strip() == "hello"


class TestContainall:
    def test_containall_hides_home(self, sif_image: str) -> None:
        """Verify $HOME inside container is NOT the host home directory."""
        host_home = os.environ.get("HOME", "")
        result = run_in_container(sif_image, "echo $HOME")
        container_home = result.stdout.strip()
        assert container_home != host_home, (
            f"Container home ({container_home}) should differ from host home ({host_home})"
        )

    def test_cleanenv_strips_variables(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "echo ${SANDBOX_TEST_VAR:-unset}",
            env_vars={},
        )
        assert "unset" in result.stdout

    def test_explicit_env_passthrough(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "echo $MY_VAR",
            env_vars={"MY_VAR": "hello123"},
        )
        assert "hello123" in result.stdout

    def test_tmp_is_isolated(self, sif_image: str, tmp_path: Path) -> None:
        """Write a uniquely-named file to /tmp inside container, verify it's not on host."""
        marker = str(uuid.uuid4())
        result = run_in_container(
            sif_image,
            f"echo '{marker}' > /tmp/sandbox-test-{marker}.txt && cat /tmp/sandbox-test-{marker}.txt",
        )
        assert marker in result.stdout
        host_path = f"/tmp/sandbox-test-{marker}.txt"
        assert not os.path.exists(host_path), "Container /tmp leaked to host /tmp"

    def test_unmounted_paths_invisible(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "ls /projects 2>&1 || echo 'NOT_FOUND'",
        )
        assert "NOT_FOUND" in result.stdout or "No such file" in result.stderr

    def test_dev_is_minimal(self, sif_image: str) -> None:
        """Verify /dev contains only essential devices, not the full host /dev."""
        result = run_in_container(sif_image, "ls /dev/")
        assert result.returncode == 0
        dev_contents = result.stdout.strip().split()
        assert "null" in dev_contents
        assert "zero" in dev_contents
        assert "urandom" in dev_contents
        assert "sda" not in dev_contents, "/dev/sda found — host /dev is exposed"
