from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click

from sandbox import __version__
from sandbox.config import load_config, TaskConfig
from sandbox.container import build_apptainer_cmd
from sandbox.slurm import detect_slurm_context, build_srun_cmd, SlurmContext
from sandbox.profiles import get_profile


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """HPC Agent Sandbox - run AI agents in isolated containers."""
    pass


@cli.command()
@click.option("--task", required=True, type=click.Path(exists=True), help="Path to task YAML config")
@click.option("--no-agent", is_flag=True, help="Drop into plain bash instead of Claude Code")
@click.option("--new-alloc", is_flag=True, help="Force a new SLURM allocation")
@click.option("--ssh", "ssh_mode", is_flag=True, help="Start with SSH server for IDE access")
@click.option("--port", type=int, default=None, help="SSH port (default: auto-select)")
def shell(task: str, no_agent: bool, new_alloc: bool, ssh_mode: bool, port: int | None) -> None:
    """Launch an interactive sandbox session."""
    config = load_config(Path(task))
    profile = get_profile()

    # Create task directory structure
    task_dir = os.path.join(profile.tasks_dir, config.task_id)
    output_dir = os.path.join(task_dir, "output")
    logs_dir = os.path.join(task_dir, "logs")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # Run setup.copy operations
    for copy_spec in config.setup.copy:
        dest = os.path.join(output_dir, os.path.basename(copy_spec.dest))
        click.echo(f"Copying {copy_spec.src} -> {dest}")
        subprocess.run(["cp", "-r", copy_spec.src, dest], check=True)

    # Save config snapshot
    import shutil
    shutil.copy2(task, os.path.join(logs_dir, "task.yaml"))

    # Determine entrypoint
    entrypoint = "bash" if no_agent else None

    if ssh_mode:
        _run_ssh_mode(config, task_dir, output_dir, port, entrypoint)
        return

    # Build apptainer command
    apptainer_cmd = build_apptainer_cmd(
        config, output_dir=output_dir, entrypoint_override=entrypoint
    )

    # Detect SLURM context and run
    ctx = detect_slurm_context(force_new_alloc=new_alloc)

    if ctx == SlurmContext.COMPUTE_NODE:
        click.echo(f"Running on compute node (job {os.environ.get('SLURM_JOB_ID')})")
        click.echo(f"Task: {config.task_id}")
        click.echo(f"Output: {output_dir}")
        result = subprocess.run(apptainer_cmd)
    else:
        click.echo("Requesting SLURM allocation...")
        srun_cmd = build_srun_cmd(config)
        full_cmd = srun_cmd + apptainer_cmd
        click.echo(f"Task: {config.task_id}")
        click.echo(f"Output: {output_dir}")
        result = subprocess.run(full_cmd)

    # Post-run audit
    _generate_manifest(output_dir, logs_dir)
    click.echo(f"\nSession ended (exit code: {result.returncode})")
    click.echo(f"Outputs: {output_dir}")
    click.echo(f"Logs: {logs_dir}")
    sys.exit(result.returncode)


def _generate_manifest(output_dir: str, logs_dir: str) -> None:
    """Generate SHA-256 manifest of all output files."""
    from sandbox.audit import generate_manifest
    generate_manifest(output_dir, logs_dir)


def _run_ssh_mode(
    config: TaskConfig, task_dir: str, output_dir: str,
    port: int | None, entrypoint_override: str | None,
) -> None:
    """Handle SSH mode — delegated to ssh module."""
    from sandbox.ssh import run_ssh_session
    run_ssh_session(config, task_dir, output_dir, port, entrypoint_override)
