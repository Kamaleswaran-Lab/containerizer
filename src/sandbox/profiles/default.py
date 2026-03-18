from __future__ import annotations

import os
import getpass
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DefaultProfile:
    scratch_base: str = field(default_factory=lambda: os.environ.get(
        "SANDBOX_SCRATCH", f"/work/{getpass.getuser()}"
    ))
    sandbox_dir: str = "sandbox"
    default_partition: str = "general"
    default_time: str = "02:00:00"
    default_cpus: int = 4
    default_mem_gb: int = 16
    gpu_flag: str = "--nv"
    image_dir: str = field(default_factory=lambda: os.environ.get(
        "SANDBOX_IMAGE_DIR", f"/work/{getpass.getuser()}/sandbox/images"
    ))

    @property
    def tasks_dir(self) -> str:
        return os.path.join(self.scratch_base, self.sandbox_dir, "tasks")

    @property
    def ide_cache_dir(self) -> str:
        return os.path.join(self.scratch_base, self.sandbox_dir, "ide-cache")
