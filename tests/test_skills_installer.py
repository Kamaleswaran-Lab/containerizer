"""Tests for sandbox.skills_installer."""

from __future__ import annotations

from pathlib import Path

from sandbox.skills_installer import (
    detect_platform,
    get_target_dir,
    install_skills,
    SKILL_FILES,
    REFERENCE_FILES,
)


class TestDetectPlatform:
    """Tests use a fake home to avoid real ~/.claude interfering."""

    def test_detects_claude_from_cwd(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        (cwd / ".claude").mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "claude"

    def test_detects_cursor(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        (cwd / ".cursor").mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "cursor"

    def test_detects_gemini(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        (cwd / ".gemini").mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "gemini"

    def test_fallback_to_generic(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "generic"

    def test_claude_takes_priority_over_cursor(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        (cwd / ".claude").mkdir()
        (cwd / ".cursor").mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "claude"

    def test_falls_back_to_home_claude(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        (tmp_path / ".claude").mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "claude"

    def test_falls_back_to_home_gemini(self, tmp_path: Path) -> None:
        cwd = tmp_path / "project"
        cwd.mkdir()
        (tmp_path / ".gemini").mkdir()
        assert detect_platform(cwd=cwd, home=tmp_path) == "gemini"


class TestGetTargetDir:
    def test_claude_project(self) -> None:
        target = get_target_dir("claude", global_install=False)
        assert target == Path.cwd() / ".claude" / "commands"

    def test_claude_global(self) -> None:
        target = get_target_dir("claude", global_install=True)
        assert target == Path.home() / ".claude" / "commands"

    def test_cursor_project(self) -> None:
        target = get_target_dir("cursor", global_install=False)
        assert target == Path.cwd() / ".cursor" / "rules"

    def test_gemini_project(self) -> None:
        target = get_target_dir("gemini", global_install=False)
        assert target == Path.cwd() / ".gemini"

    def test_generic(self) -> None:
        target = get_target_dir("generic")
        assert target == Path.cwd() / "skills"


class TestInstallSkills:
    def test_installs_all_files(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.chdir(tmp_path)
        installed = install_skills("generic")

        # Check all skill files exist
        skills_dir = tmp_path / "skills"
        assert (skills_dir / "sandbox-install.md").exists()
        assert (skills_dir / "sandbox-configure.md").exists()
        assert (skills_dir / "sandbox-reference.md").exists()
        assert (skills_dir / "references" / "template.yaml").exists()

        assert len(installed) == len(SKILL_FILES) + len(REFERENCE_FILES)

    def test_idempotent(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.chdir(tmp_path)
        first = install_skills("generic")
        second = install_skills("generic")
        assert len(first) == len(second)
        # Files still exist after second install
        for path in second:
            assert path.exists()

    def test_installed_files_have_content(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.chdir(tmp_path)
        install_skills("generic")
        skills_dir = tmp_path / "skills"
        for name in SKILL_FILES:
            content = (skills_dir / f"{name}.md").read_text()
            assert len(content) > 100, f"{name}.md is too small"

    def test_claude_platform_target(self, tmp_path: Path, monkeypatch: object) -> None:
        monkeypatch.chdir(tmp_path)
        installed = install_skills("claude")
        commands_dir = tmp_path / ".claude" / "commands"
        assert commands_dir.is_dir()
        assert (commands_dir / "sandbox-install.md").exists()
