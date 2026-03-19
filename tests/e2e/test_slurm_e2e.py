"""E2E tests for SLURM allocation + container execution."""
from __future__ import annotations

import json
import os
import subprocess

import pytest
import yaml

from sandbox.config import TaskConfig
from sandbox.container import build_apptainer_cmd
from sandbox.slurm import build_srun_cmd


pytestmark = pytest.mark.e2e


class TestSrunContainerExec:
    """Test 1: Allocate a node via srun, run a command, verify output."""

    def test_srun_echo(self, e2e_task_config, e2e_output_dir, sif_image):
        with open(e2e_task_config) as f:
            data = yaml.safe_load(f)
        config = TaskConfig.from_dict(data)

        apptainer_cmd = build_apptainer_cmd(
            config,
            output_dir=e2e_output_dir,
            entrypoint_override="echo E2E_SUCCESS",
        )

        srun_cmd = build_srun_cmd(config)
        # Drop --pty for non-interactive captured-output runs
        srun_cmd = [arg for arg in srun_cmd if arg != "--pty"]

        result = subprocess.run(
            srun_cmd + apptainer_cmd,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, (
            f"srun+apptainer failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "E2E_SUCCESS" in result.stdout


class TestSrunClaudeInvocation:
    """Test 2: Allocate a node, run Claude Code with a prompt, verify output."""

    def test_claude_responds(self, e2e_task_config, e2e_output_dir, sif_image):
        claude_dir = os.path.expanduser("~/.claude")
        if not os.path.isdir(claude_dir):
            pytest.skip("~/.claude not found — no Claude auth configured")

        with open(e2e_task_config) as f:
            data = yaml.safe_load(f)
        config = TaskConfig.from_dict(data)

        apptainer_cmd = build_apptainer_cmd(
            config,
            output_dir=e2e_output_dir,
            entrypoint_override=(
                'claude -p "respond with exactly: E2E_CLAUDE_OK" --output-format text'
            ),
        )

        srun_cmd = build_srun_cmd(config)
        srun_cmd = [arg for arg in srun_cmd if arg != "--pty"]

        result = subprocess.run(
            srun_cmd + apptainer_cmd,
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, (
            f"Claude invocation failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "E2E_CLAUDE_OK" in result.stdout


class TestSrunAuditTrail:
    """Test 3: Run full sandbox shell flow, verify audit artifacts."""

    def test_audit_artifacts(self, e2e_task_config):
        result = subprocess.run(
            ["uv", "run", "sandbox", "shell", "--task", e2e_task_config, "--no-agent"],
            input="echo AUDIT_TEST && exit\n",
            capture_output=True,
            text=True,
            timeout=180,
        )

        assert result.returncode == 0, (
            f"sandbox shell failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Find the task directory created by the CLI
        from sandbox.profiles import get_profile
        profile = get_profile()
        tasks_dir = profile.tasks_dir

        # Look for the most recent e2e-test-* directory
        task_dirs = sorted(
            [
                d for d in os.listdir(tasks_dir)
                if d.startswith("e2e-test-")
            ],
            reverse=True,
        )
        assert task_dirs, f"No e2e-test-* task dir found in {tasks_dir}"
        task_dir = os.path.join(tasks_dir, task_dirs[0])

        # Verify audit artifacts
        meta_path = os.path.join(task_dir, "logs", "meta.json")
        manifest_path = os.path.join(task_dir, "logs", "manifest.txt")

        assert os.path.exists(meta_path), f"meta.json not found at {meta_path}"
        assert os.path.exists(manifest_path), f"manifest.txt not found at {manifest_path}"

        with open(meta_path) as f:
            meta = json.load(f)

        assert "task_id" in meta
        assert "exit_code" in meta
        assert "start_time" in meta
        assert "end_time" in meta
        assert "node" in meta
        assert meta["exit_code"] == 0
