from __future__ import annotations

import pytest

from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


class TestBaseSystemImage:
    """Validate base-system.sif has OS tools but NOT Claude Code."""

    def test_system_has_python(self, base_system_image: str) -> None:
        result = run_in_container(base_system_image, "python3 --version")
        assert result.returncode == 0
        assert "Python 3" in result.stdout

    def test_system_has_node(self, base_system_image: str) -> None:
        result = run_in_container(base_system_image, "node --version")
        assert result.returncode == 0

    def test_system_has_conda(self, base_system_image: str) -> None:
        result = run_in_container(base_system_image, "/opt/conda/bin/conda --version")
        assert result.returncode == 0

    def test_system_has_sshd(self, base_system_image: str) -> None:
        result = run_in_container(base_system_image, "test -x /usr/sbin/sshd")
        assert result.returncode == 0

    def test_system_has_core_tools(self, base_system_image: str) -> None:
        result = run_in_container(
            base_system_image,
            "git --version && curl --version > /dev/null && jq --version",
        )
        assert result.returncode == 0

    def test_system_lacks_claude(self, base_system_image: str) -> None:
        result = run_in_container(
            base_system_image,
            "which claude && npm list -g @anthropic-ai/claude-code",
        )
        assert result.returncode != 0

    def test_system_lacks_profile_script(self, base_system_image: str) -> None:
        result = run_in_container(
            base_system_image,
            "test -f /etc/profile.d/sandbox-env.sh",
        )
        assert result.returncode != 0


class TestBaseAgentImage:
    """Validate base-agent.sif layers Claude Code + profile script on top."""

    def test_agent_has_claude(self, sif_image: str) -> None:
        result = run_in_container(sif_image, "which claude")
        assert result.returncode == 0

    def test_agent_has_profile_script(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "test -f /etc/profile.d/sandbox-env.sh",
        )
        assert result.returncode == 0
