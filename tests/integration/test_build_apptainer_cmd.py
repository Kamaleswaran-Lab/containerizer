from __future__ import annotations

import os
import subprocess

import pytest
from pathlib import Path

from sandbox.config import TaskConfig, MountsConfig, MountSpec, ResourcesConfig, DepsConfig, SetupConfig
from sandbox.container import build_apptainer_cmd
from tests.integration.conftest import _find_image


pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(autouse=True)
def set_image_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point SANDBOX_IMAGE_DIR at repo_root/images/ so image paths resolve."""
    monkeypatch.setenv("SANDBOX_IMAGE_DIR", str(REPO_ROOT / "images"))


def _make_config(
    output_dir: Path,
    mounts: MountsConfig | None = None,
    conda_env: str | None = None,
) -> TaskConfig:
    return TaskConfig(
        task_id="test-cmd-001",
        image="base-agent.sif",
        mounts=mounts or MountsConfig(),
        resources=ResourcesConfig(),
        setup=SetupConfig(),
        deps=DepsConfig(conda_env=conda_env),
        entrypoint="bash",
    )


def _run_cmd(cmd: list[str], shell_cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a build_apptainer_cmd result with an appended shell command."""
    full = cmd + ["-c", shell_cmd]
    return subprocess.run(full, capture_output=True, text=True, timeout=timeout)


class TestBuildApptainerCmd:
    def test_generated_cmd_runs(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config = _make_config(output_dir)
        cmd = build_apptainer_cmd(config, str(output_dir), entrypoint_override="bash")
        result = _run_cmd(cmd, "echo OK")
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_input_mount_via_cmd(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "file.txt").write_text("mount-test-data")

        mounts = MountsConfig(
            inputs=[MountSpec(src=str(input_dir), dest="/input")],
        )
        config = _make_config(output_dir, mounts=mounts)
        cmd = build_apptainer_cmd(config, str(output_dir), entrypoint_override="bash")
        result = _run_cmd(cmd, "cat /input/file.txt")
        assert result.returncode == 0
        assert "mount-test-data" in result.stdout

    def test_output_mount_via_cmd(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config = _make_config(output_dir)
        cmd = build_apptainer_cmd(config, str(output_dir), entrypoint_override="bash")
        _run_cmd(cmd, "echo 'written-via-cmd' > /output/result.txt")
        assert (output_dir / "result.txt").read_text().strip() == "written-via-cmd"

    def test_home_is_sandbox_home(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config = _make_config(output_dir)
        cmd = build_apptainer_cmd(config, str(output_dir), entrypoint_override="bash")
        result = _run_cmd(cmd, "echo $HOME")
        assert result.stdout.strip() == "/home/sandbox"

    def test_env_mount_readonly(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        (env_dir / "env.txt").write_text("readonly")

        mounts = MountsConfig(
            environment=[MountSpec(src=str(env_dir), dest="/env")],
        )
        config = _make_config(output_dir, mounts=mounts)
        cmd = build_apptainer_cmd(config, str(output_dir), entrypoint_override="bash")
        result = _run_cmd(cmd, "touch /env/new.txt 2>&1; echo EXIT=$?")
        assert "EXIT=1" in result.stdout or result.returncode != 0
