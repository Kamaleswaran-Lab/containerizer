from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from sandbox.config import TaskConfig
from sandbox.container import build_apptainer_cmd


class TestBuildApptainerCmd:
    def test_basic_command_structure(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/work/user/sandbox/tasks/test/output")
        assert cmd[0] == "apptainer"
        assert cmd[1] == "exec"
        assert "--containall" in cmd
        assert "--cleanenv" in cmd

    def test_readonly_input_mounts(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/work/user/sandbox/tasks/test/output")
        cmd_str = " ".join(cmd)
        input_src = minimal_config["mounts"]["inputs"][0]["src"]
        assert f"--bind {input_src}:/input/data:ro" in cmd_str

    def test_output_mount_readwrite(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/work/user/sandbox/tasks/test/output")
        cmd_str = " ".join(cmd)
        assert "--bind /work/user/sandbox/tasks/test/output:/output:rw" in cmd_str

    def test_dns_mount_always_present(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        cmd_str = " ".join(cmd)
        assert "--bind /etc/resolv.conf:/etc/resolv.conf:ro" in cmd_str

    def test_gpu_flag_when_gpu_requested(self, minimal_config: dict) -> None:
        minimal_config["resources"]["gpu"] = 1
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        assert "--nv" in cmd

    def test_no_gpu_flag_when_no_gpu(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        assert "--nv" not in cmd

    def test_claude_auth_mount_uses_container_home(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        with patch.dict("os.environ", {"HOME": "/home/testuser"}):
            with patch("sandbox.container.os.path.isdir", return_value=True):
                cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        cmd_str = " ".join(cmd)
        assert "/home/testuser/.claude:/home/sandbox/.claude:rw" in cmd_str

    def test_conda_env_passed_as_env_var(self, minimal_config: dict) -> None:
        minimal_config["deps"] = {"conda_env": "ml"}
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        cmd_str = " ".join(cmd)
        assert "--env SANDBOX_CONDA_ENV=ml" in cmd_str

    def test_environment_mounts_readonly(self, minimal_config: dict, tmp_path: Path) -> None:
        env_dir = tmp_path / "envs" / "ml"
        env_dir.mkdir(parents=True)
        minimal_config["mounts"]["environment"] = [
            {"src": str(env_dir), "dest": "/opt/conda/envs/ml"}
        ]
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        cmd_str = " ".join(cmd)
        assert f"--bind {env_dir}:/opt/conda/envs/ml:ro" in cmd_str

    def test_api_key_passed_via_env(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-123"}):
            cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        cmd_str = " ".join(cmd)
        assert "--env ANTHROPIC_API_KEY=sk-test-123" in cmd_str

    def test_entrypoint_is_last(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        assert cmd[-1] == "claude"

    def test_image_resolved_from_profile(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_apptainer_cmd(config, output_dir="/tmp/out")
        assert any("base-agent.sif" in arg for arg in cmd)
