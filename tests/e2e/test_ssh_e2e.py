"""E2E tests for SSH access into SLURM-allocated containers."""
from __future__ import annotations

import glob
import os
import re
import shutil
import signal
import socket
import subprocess
import time

import pytest
import yaml

from sandbox.config import TaskConfig
from sandbox.container import build_apptainer_cmd
from sandbox.slurm import build_srun_cmd
from sandbox.ssh import generate_sshd_config, select_port


pytestmark = pytest.mark.e2e


def _find_ssh_dir() -> str | None:
    """Find the user's .ssh directory, checking $HOME and passwd home."""
    candidates = [os.path.expanduser("~/.ssh")]
    # Fall back to passwd entry home if $HOME was overridden
    try:
        import pwd
        pw_home = pwd.getpwuid(os.getuid()).pw_dir
        pw_ssh = os.path.join(pw_home, ".ssh")
        if pw_ssh not in candidates:
            candidates.append(pw_ssh)
    except (KeyError, ImportError):
        pass
    for d in candidates:
        if os.path.isdir(d):
            return d
    return None


def _get_user_pubkeys() -> list[str]:
    """Collect the user's SSH public keys."""
    ssh_dir = _find_ssh_dir()
    pubkeys = []
    if ssh_dir:
        for path in glob.glob(os.path.join(ssh_dir, "*.pub")):
            with open(path) as f:
                content = f.read().strip()
                if content:
                    pubkeys.append(content)
    return pubkeys


def _wait_for_ssh(host: str, port: int, user: str, timeout: float = 60.0) -> bool:
    """Poll until SSH connection succeeds or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            [
                "ssh",
                "-p", str(port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=3",
                "-o", "BatchMode=yes",
                f"{user}@{host}",
                "echo SSH_READY",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and "SSH_READY" in result.stdout:
            return True
        time.sleep(2)
    return False


def _ssh_run(host: str, port: int, user: str, command: str) -> subprocess.CompletedProcess:
    """Execute a command over SSH."""
    return subprocess.run(
        [
            "ssh",
            "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "BatchMode=yes",
            f"{user}@{host}",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _parse_node_from_srun(job_name: str, timeout: float = 60.0) -> str | None:
    """Detect the compute node by polling squeue for the job name."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        sq = subprocess.run(
            ["squeue", "--me", "--name", job_name, "--format=%N", "--noheader"],
            capture_output=True, text=True, timeout=10,
        )
        node = sq.stdout.strip()
        if node:
            return node
        time.sleep(2)
    return None


class _SSHFixture:
    """Manages the lifecycle of an sshd container for SSH tests."""

    def __init__(self, e2e_scratch, e2e_output_dir, sif_image, e2e_task_config):
        self.scratch = e2e_scratch
        self.output_dir = e2e_output_dir
        self.sif_image = sif_image
        self.task_config_path = e2e_task_config
        self.proc: subprocess.Popen | None = None
        self.node: str | None = None
        self.port: int | None = None
        self.user = os.environ.get("USER", "sandbox")
        self.sshd_dir: str | None = None
        self._job_id: str | None = None

    def start(self) -> None:
        # Load task config
        with open(self.task_config_path) as f:
            data = yaml.safe_load(f)
        config = TaskConfig.from_dict(data)

        # Set up sshd dir and config
        self.sshd_dir = os.path.join(self.scratch, "sshd")
        os.makedirs(self.sshd_dir, exist_ok=True)
        self.port = select_port(None, None)
        generate_sshd_config(self.sshd_dir, self.port)

        # Write authorized_keys into sshd_dir (mounted at /run/sshd)
        # so it isn't overlaid by the ~/.ssh bind mount
        pubkeys = _get_user_pubkeys()
        ak_path = os.path.join(self.sshd_dir, "authorized_keys")
        with open(ak_path, "w") as f:
            f.write("\n".join(pubkeys) + "\n" if pubkeys else "")
        os.chmod(ak_path, 0o600)

        # Build apptainer command with SSH mode
        # Pass full sshd command as entrypoint so bash -l -c gets the whole string
        apptainer_cmd = build_apptainer_cmd(
            config,
            output_dir=self.output_dir,
            ssh_mode=True,
            sshd_dir=self.sshd_dir,
            entrypoint_override="/usr/sbin/sshd -D -f /run/sshd/sshd_config",
        )

        # If already on a compute node, run apptainer directly; otherwise use srun
        on_compute = "SLURM_JOB_ID" in os.environ
        if on_compute:
            full_cmd = apptainer_cmd
            self.node = socket.gethostname()
        else:
            srun_cmd = build_srun_cmd(config)
            srun_cmd = [arg for arg in srun_cmd if arg != "--pty"]
            full_cmd = srun_cmd + apptainer_cmd

        self.proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if not on_compute:
            # Wait for allocation and get node name
            job_name = f"sandbox-{config.task_id}"
            self.node = _parse_node_from_srun(job_name)
            if not self.node:
                self.stop()
                pytest.fail("Could not determine compute node from srun output")

        # Wait for sshd to be ready
        if not _wait_for_ssh(self.node, self.port, self.user):
            self.stop()
            pytest.fail(
                f"SSH not ready after 60s on {self.node}:{self.port}"
            )

    def stop(self) -> None:
        if self.proc:
            try:
                self.proc.send_signal(signal.SIGTERM)
                self.proc.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
                except Exception:
                    pass

        # Also scancel any remaining jobs for this test
        try:
            result = subprocess.run(
                ["squeue", "--me", "--format=%i %j", "--noheader"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split(None, 1)
                if len(parts) == 2 and "e2e-test" in parts[1]:
                    subprocess.run(
                        ["scancel", parts[0]],
                        capture_output=True, timeout=10,
                    )
        except Exception:
            pass


@pytest.fixture
def ssh_session(e2e_scratch, e2e_output_dir, sif_image, e2e_task_config):
    """Start an sshd container via srun and provide the connection details."""
    fixture = _SSHFixture(e2e_scratch, e2e_output_dir, sif_image, e2e_task_config)
    try:
        fixture.start()
        yield fixture
    finally:
        fixture.stop()


class TestSSHLogin:
    """Test 4: SSH into a SLURM-allocated container and run a command."""

    def test_ssh_echo(self, ssh_session):
        result = _ssh_run(
            ssh_session.node,
            ssh_session.port,
            ssh_session.user,
            "echo SSH_E2E_OK",
        )
        assert result.returncode == 0, (
            f"SSH command failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "SSH_E2E_OK" in result.stdout


class TestSSHFilePersistence:
    """Test 5: Write a file via SSH, verify it persists on the host."""

    def test_file_persists(self, ssh_session):
        # Write a file to /output inside the container
        result = _ssh_run(
            ssh_session.node,
            ssh_session.port,
            ssh_session.user,
            "echo PERSIST_TEST > /output/e2e_test.txt",
        )
        assert result.returncode == 0, (
            f"SSH write failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify the file exists on the host
        host_path = os.path.join(ssh_session.output_dir, "e2e_test.txt")
        assert os.path.exists(host_path), (
            f"File not found on host at {host_path}"
        )
        with open(host_path) as f:
            content = f.read().strip()
        assert content == "PERSIST_TEST"
