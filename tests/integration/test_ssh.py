from __future__ import annotations

import os
import subprocess
import time

import pytest
from pathlib import Path

from sandbox.ssh import select_port, generate_sshd_config
from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


class TestSSHPortSelection:
    def test_select_port_with_job_id(self) -> None:
        port = select_port("12345", explicit_port=None)
        assert 2222 <= port < 3222

    def test_explicit_port_used(self) -> None:
        port = select_port("12345", explicit_port=3333)
        assert port == 3333

    def test_port_collision_gets_next(self) -> None:
        """Two calls with same job_id should return the same base port."""
        port1 = select_port("12345", explicit_port=None)
        port2 = select_port("12345", explicit_port=None)
        assert port1 == port2


class TestSSHDConfig:
    def test_sshd_config_generated(self, tmp_path: Path) -> None:
        sshd_dir = str(tmp_path / "sshd")
        os.makedirs(sshd_dir)
        config_path = generate_sshd_config(sshd_dir, 2222)
        assert os.path.exists(config_path)
        content = open(config_path).read()
        assert "Port 2222" in content
        assert "PasswordAuthentication no" in content

    def test_host_key_generated(self, tmp_path: Path) -> None:
        sshd_dir = str(tmp_path / "sshd")
        os.makedirs(sshd_dir)
        generate_sshd_config(sshd_dir, 2222)
        assert os.path.exists(os.path.join(sshd_dir, "ssh_host_ed25519_key"))


class TestSSHDInContainer:
    def test_sshd_starts_on_high_port(self, sif_image: str, tmp_path: Path) -> None:
        """Verify SSHD can start inside the container on a non-privileged port."""
        sshd_dir = tmp_path / "sshd"
        sshd_dir.mkdir()
        config_path = generate_sshd_config(str(sshd_dir), 2299)

        # Start SSHD in background, check it binds, then kill
        result = run_in_container(
            sif_image,
            f"/usr/sbin/sshd -f {config_path} -D -e &"
            f" SSHD_PID=$!; sleep 1;"
            f" ss -tlnp | grep 2299 && echo 'PORT_BOUND';"
            f" kill $SSHD_PID 2>/dev/null; wait $SSHD_PID 2>/dev/null; exit 0",
            binds=[f"{sshd_dir}:/run/sshd:rw"],
        )
        assert "PORT_BOUND" in result.stdout
