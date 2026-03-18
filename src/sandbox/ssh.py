from __future__ import annotations

import os
import socket
import subprocess
import sys

import click

from sandbox.config import TaskConfig
from sandbox.container import build_apptainer_cmd
from sandbox.slurm import detect_slurm_context, build_srun_cmd, SlurmContext


def select_port(job_id: str | None, explicit_port: int | None) -> int:
    """Select an SSH port, avoiding collisions."""
    if explicit_port:
        return explicit_port

    base_port = 2222
    port_range = 1000

    if job_id:
        port = base_port + (int(job_id) % port_range)
    else:
        port = base_port

    # Try the computed port, then sequential fallbacks
    for offset in range(100):
        candidate = port + offset
        if _port_available(candidate):
            return candidate

    raise RuntimeError("Could not find an available port in range")


def _port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", port))
            return True
    except OSError:
        return False


def generate_sshd_config(sshd_dir: str, port: int) -> str:
    """Generate a minimal sshd_config for the sandbox."""
    config_path = os.path.join(sshd_dir, "sshd_config")
    host_key_path = os.path.join(sshd_dir, "ssh_host_ed25519_key")

    # Generate host key if not present
    if not os.path.exists(host_key_path):
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", host_key_path, "-N", ""],
            check=True, capture_output=True,
        )

    container_home = "/home/sandbox"
    config_content = f"""\
Port {port}
ListenAddress 0.0.0.0
HostKey {host_key_path}
AuthorizedKeysFile {container_home}/.ssh/authorized_keys
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
PidFile {sshd_dir}/sshd.pid
"""
    with open(config_path, "w") as f:
        f.write(config_content)

    return config_path


def run_ssh_session(
    config: TaskConfig,
    task_dir: str,
    output_dir: str,
    port: int | None,
    entrypoint_override: str | None,
) -> None:
    """Start an SSH-accessible sandbox session."""
    sshd_dir = os.path.join(task_dir, "sshd")
    os.makedirs(sshd_dir, exist_ok=True)

    job_id = os.environ.get("SLURM_JOB_ID")
    selected_port = select_port(job_id, port)
    sshd_config = generate_sshd_config(sshd_dir, selected_port)

    # Build apptainer command with SSH mode
    apptainer_cmd = build_apptainer_cmd(
        config,
        output_dir=output_dir,
        ssh_mode=True,
        sshd_dir=sshd_dir,
        entrypoint_override="/usr/sbin/sshd",
    )
    # Append sshd flags after the entrypoint
    apptainer_cmd.extend(["-D", "-f", sshd_config])

    hostname = socket.gethostname()
    click.echo(f"Sandbox SSH mode starting...")
    click.echo(f"  Task: {config.task_id}")
    click.echo(f"  Node: {hostname}")
    click.echo(f"  Port: {selected_port}")
    click.echo(f"  Output: {output_dir}")
    click.echo(f"\nConnect with:")
    click.echo(f"  ssh -p {selected_port} {os.environ.get('USER', 'user')}@{hostname}")
    click.echo(f"\nStop with: sandbox stop --task-id {config.task_id}")
    click.echo("Waiting for connections... (Ctrl+C to stop)\n")

    ctx = detect_slurm_context()
    try:
        if ctx == SlurmContext.COMPUTE_NODE:
            result = subprocess.run(apptainer_cmd)
        else:
            srun_cmd = build_srun_cmd(config)
            result = subprocess.run(srun_cmd + apptainer_cmd)
    except KeyboardInterrupt:
        click.echo("\nShutting down SSH sandbox...")
        result = type("Result", (), {"returncode": 0})()

    from sandbox.audit import generate_manifest
    generate_manifest(output_dir, os.path.join(task_dir, "logs"))
    sys.exit(result.returncode)
