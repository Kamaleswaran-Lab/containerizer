from __future__ import annotations

import os
from enum import Enum

from sandbox.config import TaskConfig


class SlurmContext(Enum):
    LOGIN_NODE = "login_node"
    COMPUTE_NODE = "compute_node"
    NEEDS_ALLOCATION = "needs_allocation"


def detect_slurm_context(force_new_alloc: bool = False) -> SlurmContext:
    has_job = "SLURM_JOB_ID" in os.environ
    if not has_job:
        return SlurmContext.LOGIN_NODE
    if force_new_alloc:
        return SlurmContext.NEEDS_ALLOCATION
    return SlurmContext.COMPUTE_NODE


def build_srun_cmd(config: TaskConfig) -> list[str]:
    """Build srun command for interactive allocation."""
    cmd = [
        "srun",
        "--pty",
        f"--job-name=sandbox-{config.task_id}",
        f"--cpus-per-task={config.resources.cpus}",
        f"--mem={config.resources.mem_gb}G",
        f"--time={config.resources.time}",
        f"--partition={config.resources.partition}",
    ]
    if config.resources.gpu > 0:
        cmd.append(f"--gres=gpu:{config.resources.gpu}")
    return cmd
