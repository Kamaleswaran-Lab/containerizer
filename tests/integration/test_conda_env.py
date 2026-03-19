from __future__ import annotations

import pytest

from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


class TestCondaEnvironment:
    def test_conda_init_in_login_shell(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "bash -l -c 'conda info'",
            timeout=60,
        )
        assert result.returncode == 0

    def test_pythonuserbase_set(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "bash -l -c 'echo PYTHONUSERBASE=$PYTHONUSERBASE'",
        )
        assert "PYTHONUSERBASE=/output/.local" in result.stdout

    def test_pythonpath_set(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "bash -l -c 'echo PYTHONPATH=$PYTHONPATH'",
        )
        assert "site-packages" in result.stdout

    def test_conda_env_activation(self, sif_image: str) -> None:
        result = run_in_container(
            sif_image,
            "bash -l -c 'echo CONDA_DEFAULT_ENV=$CONDA_DEFAULT_ENV'",
            env_vars={"SANDBOX_CONDA_ENV": "base"},
            timeout=60,
        )
        assert "CONDA_DEFAULT_ENV=base" in result.stdout

    def test_invalid_conda_env_nonfatal(self, sif_image: str) -> None:
        """An invalid conda env name should not crash the container."""
        result = run_in_container(
            sif_image,
            "bash -l -c 'echo STILL_ALIVE'",
            env_vars={"SANDBOX_CONDA_ENV": "nonexistent_env_xyz"},
            timeout=60,
        )
        assert "STILL_ALIVE" in result.stdout
