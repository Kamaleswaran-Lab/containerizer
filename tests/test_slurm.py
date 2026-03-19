from __future__ import annotations

import pytest
from unittest.mock import patch

from sandbox.slurm import detect_slurm_context, SlurmContext, build_srun_cmd
from sandbox.config import TaskConfig


class TestSlurmDetection:
    def test_detects_login_node(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            ctx = detect_slurm_context()
        assert ctx == SlurmContext.LOGIN_NODE

    def test_detects_compute_node(self) -> None:
        with patch.dict("os.environ", {"SLURM_JOB_ID": "12345"}):
            ctx = detect_slurm_context()
        assert ctx == SlurmContext.COMPUTE_NODE

    def test_new_alloc_overrides_compute(self) -> None:
        with patch.dict("os.environ", {"SLURM_JOB_ID": "12345"}):
            ctx = detect_slurm_context(force_new_alloc=True)
        assert ctx == SlurmContext.NEEDS_ALLOCATION


class TestSrunCommand:
    def test_srun_includes_pty(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_srun_cmd(config)
        assert "--pty" in cmd

    def test_srun_includes_resources(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_srun_cmd(config)
        cmd_str = " ".join(cmd)
        assert "--cpus-per-task=2" in cmd_str
        assert "--mem=8G" in cmd_str
        assert "--time=01:00:00" in cmd_str

    def test_srun_includes_gpu_when_requested(self, minimal_config: dict) -> None:
        minimal_config["resources"]["gpu"] = 2
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_srun_cmd(config)
        cmd_str = " ".join(cmd)
        assert "--gres=gpu:2" in cmd_str

    def test_srun_no_gpu_flag_when_zero(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        cmd = build_srun_cmd(config)
        cmd_str = " ".join(cmd)
        assert "--gres" not in cmd_str
