from __future__ import annotations

import pytest
from pathlib import Path

from tests.integration.conftest import run_in_container


pytestmark = pytest.mark.integration


class TestOutputPersistence:
    def test_files_survive_exit(self, sif_image: str, output_dir: Path) -> None:
        run_in_container(
            sif_image,
            "echo 'persist-test' > /output/survived.txt",
            binds=[f"{output_dir}:/output:rw"],
        )
        assert (output_dir / "survived.txt").read_text().strip() == "persist-test"

    def test_nested_dirs(self, sif_image: str, output_dir: Path) -> None:
        run_in_container(
            sif_image,
            "mkdir -p /output/a/b/c && echo 'deep' > /output/a/b/c/f.txt",
            binds=[f"{output_dir}:/output:rw"],
        )
        assert (output_dir / "a" / "b" / "c" / "f.txt").read_text().strip() == "deep"

    def test_home_writes_go_to_output(self, sif_image: str, output_dir: Path) -> None:
        """With --home output:/home/sandbox, writes to ~ should land in output_dir."""
        run_in_container(
            sif_image,
            "echo 'home-test' > ~/file.txt",
            extra_flags=[f"--home", f"{output_dir}:/home/sandbox"],
        )
        assert (output_dir / "file.txt").read_text().strip() == "home-test"

    def test_dotfiles_persist(self, sif_image: str, output_dir: Path) -> None:
        run_in_container(
            sif_image,
            "echo 'alias ll=ls' > ~/.bashrc_custom",
            extra_flags=[f"--home", f"{output_dir}:/home/sandbox"],
        )
        assert (output_dir / ".bashrc_custom").read_text().strip() == "alias ll=ls"
