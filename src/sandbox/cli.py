from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click

from sandbox import __version__
from sandbox.config import load_config, TaskConfig
from sandbox.container import build_apptainer_cmd
from sandbox.slurm import detect_slurm_context, build_srun_cmd, SlurmContext
from sandbox.profiles import get_profile
from sandbox.cleanup import find_task_dirs, remove_task, parse_duration


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


@cli.command()
@click.option("--task-id", required=True, help="Task ID to inspect")
def audit(task_id: str) -> None:
    """Show audit information for a completed task."""
    profile = get_profile()
    task_dir = Path(profile.tasks_dir) / task_id
    if not task_dir.exists():
        # Try prefix match
        matches = list(Path(profile.tasks_dir).glob(f"{task_id}*"))
        if len(matches) == 1:
            task_dir = matches[0]
        elif len(matches) > 1:
            click.echo(f"Multiple matches for '{task_id}':")
            for m in matches:
                click.echo(f"  {m.name}")
            return
        else:
            click.echo(f"Task not found: {task_id}")
            return

    meta_path = task_dir / "logs" / "meta.json"
    manifest_path = task_dir / "logs" / "manifest.txt"

    if meta_path.exists():
        click.echo("=== Metadata ===")
        click.echo(meta_path.read_text())

    if manifest_path.exists():
        click.echo("\n=== Output Manifest ===")
        click.echo(manifest_path.read_text())


@cli.command()
@click.option("--older-than", default=None, help="Remove tasks older than duration (e.g., 7d, 24h)")
@click.option("--task-id", default=None, help="Remove a specific task")
@click.option("--dry-run", is_flag=True, help="Show what would be removed")
@click.option("--ide-cache", is_flag=True, help="Also clear IDE server cache")
def cleanup(older_than: str | None, task_id: str | None, dry_run: bool, ide_cache: bool) -> None:
    """Remove old task directories and logs."""
    profile = get_profile()

    if task_id:
        task_dir = Path(profile.tasks_dir) / task_id
        matches = [task_dir] if task_dir.exists() else list(Path(profile.tasks_dir).glob(f"{task_id}*"))
        if not matches:
            click.echo(f"Task not found: {task_id}")
            return
        dirs_to_remove = matches
    elif older_than:
        seconds = parse_duration(older_than)
        dirs_to_remove = find_task_dirs(older_than_seconds=seconds)
    else:
        click.echo("Specify --older-than or --task-id")
        return

    for d in dirs_to_remove:
        if dry_run:
            click.echo(f"Would remove: {d}")
        else:
            click.echo(f"Removing: {d}")
            remove_task(d)

    if ide_cache and not dry_run:
        cache_dir = Path(profile.ide_cache_dir)
        if cache_dir.exists():
            click.echo(f"Clearing IDE cache: {cache_dir}")
            shutil.rmtree(cache_dir)

    if not dirs_to_remove:
        click.echo("Nothing to clean up.")


@cli.command()
@click.option("--task-id", required=True, help="Task ID to stop")
def stop(task_id: str) -> None:
    """Stop a running sandbox task by cancelling its SLURM job."""
    # Find the SLURM job for this task
    result = subprocess.run(
        ["squeue", "--me", "--name", f"sandbox-{task_id}", "--format", "%i", "--noheader"],
        capture_output=True, text=True,
    )
    job_ids = result.stdout.strip().splitlines()

    if not job_ids:
        # Try prefix match
        result = subprocess.run(
            ["squeue", "--me", "--format", "%i %j", "--noheader"],
            capture_output=True, text=True,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and task_id in parts[1]:
                job_ids.append(parts[0])

    if not job_ids:
        click.echo(f"No running SLURM job found for task: {task_id}")
        return

    for jid in job_ids:
        click.echo(f"Cancelling SLURM job {jid}")
        subprocess.run(["scancel", jid], check=True)
    click.echo("Done.")
