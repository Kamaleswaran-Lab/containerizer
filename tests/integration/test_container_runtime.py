from __future__ import annotations

import pytest

from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


class TestNetworkAccess:
    def test_dns_resolution(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "getent hosts api.anthropic.com",
        )
        assert result.returncode == 0

    def test_network_access(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "curl -s -o /dev/null -w '%{http_code}' https://api.anthropic.com",
        )
        assert result.returncode == 0


class TestProfileScript:
    def test_profile_d_loaded_in_login_shell(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "bash -l -c 'echo PYTHONUSERBASE=$PYTHONUSERBASE'",
        )
        assert "PYTHONUSERBASE=/output/.local" in result.stdout

    def test_conda_available(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "bash -l -c 'which conda'",
        )
        assert result.returncode == 0


class TestTooling:
    def test_claude_installed(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "which claude || npm list -g @anthropic-ai/claude-code",
        )
        assert result.returncode == 0

    def test_python3_available(self, sif_image: str) -> None:
        result = run_in_container(sif_image, "python3 --version")
        assert result.returncode == 0
        assert "Python 3" in result.stdout

    def test_node_available(self, sif_image: str) -> None:
        result = run_in_container(sif_image, "node --version")
        assert result.returncode == 0

    def test_git_available(self, sif_image: str) -> None:
        result = run_in_container(sif_image, "git --version")
        assert result.returncode == 0
