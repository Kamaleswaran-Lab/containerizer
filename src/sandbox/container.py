from __future__ import annotations

import os
from pathlib import Path

from sandbox.config import TaskConfig
from sandbox.profiles import get_profile


def build_apptainer_cmd(
    config: TaskConfig,
    output_dir: str,
    ssh_mode: bool = False,
    sshd_dir: str | None = None,
    entrypoint_override: str | None = None,
) -> list[str]:
    """Build the full apptainer exec command with all mounts and flags."""
    profile = get_profile()
    cmd: list[str] = ["apptainer", "exec", "--containall", "--cleanenv"]

    # --- Bind mounts ---

    # DNS (always)
    cmd.extend(["--bind", "/etc/resolv.conf:/etc/resolv.conf:ro"])

    # Input mounts (read-only)
    for mount in config.mounts.inputs:
        cmd.extend(["--bind", f"{mount.src}:{mount.dest}:ro"])

    # Environment mounts (read-only)
    for mount in config.mounts.environment:
        cmd.extend(["--bind", f"{mount.src}:{mount.dest}:ro"])

    # Output workspace (read-write)
    cmd.extend(["--bind", f"{output_dir}:/output:rw"])

    # Container home directory (--containall sets home to /root for non-root users
    # on some versions, or /home/$USER. We use --home to set it explicitly.)
    container_home = "/home/sandbox"
    cmd.extend(["--home", f"{output_dir}:{container_home}"])

    # Claude Code auth tokens (read-write) — mount to container home, not host home
    home = os.environ.get("HOME", "")
    claude_dir = os.path.join(home, ".claude")
    if os.path.isdir(claude_dir):
        cmd.extend(["--bind", f"{claude_dir}:{container_home}/.claude:rw"])

    # Claude Code config file
    claude_json = os.path.join(home, ".claude.json")
    if os.path.isfile(claude_json):
        cmd.extend(["--bind", f"{claude_json}:{container_home}/.claude.json:rw"])

    # SSH mode mounts
    if ssh_mode:
        ssh_dir = os.path.join(home, ".ssh")
        if os.path.isdir(ssh_dir):
            cmd.extend(["--bind", f"{ssh_dir}:{container_home}/.ssh:ro"])

        # IDE cache — mount to container home paths
        for ide_dir in [".cursor-server", ".vscode-server"]:
            cache_path = os.path.join(profile.ide_cache_dir, ide_dir)
            os.makedirs(cache_path, exist_ok=True)
            cmd.extend(["--bind", f"{cache_path}:{container_home}/{ide_dir}:rw"])

        # SSHD runtime
        if sshd_dir:
            cmd.extend(["--bind", f"{sshd_dir}:/run/sshd:rw"])

    # GPU
    if config.resources.gpu > 0:
        cmd.append("--nv")

    # --- Environment variables ---

    # API key passthrough
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        cmd.extend(["--env", f"ANTHROPIC_API_KEY={api_key}"])

    # Conda environment activation
    if config.deps.conda_env:
        cmd.extend(["--env", f"SANDBOX_CONDA_ENV={config.deps.conda_env}"])

    # --- Image ---
    image_path = os.path.join(profile.image_dir, config.image)
    cmd.append(image_path)

    # --- Entrypoint ---
    # Wrap in login shell so /etc/profile.d scripts run (e.g. sandbox-env.sh
    # creates the claude symlink needed when --home overlays /home/sandbox).
    entrypoint = entrypoint_override or config.entrypoint
    if entrypoint == "bash":
        cmd.extend(["bash", "-l"])
    else:
        cmd.extend(["bash", "-l", "-c", entrypoint])

    return cmd
