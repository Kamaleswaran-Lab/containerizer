from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from sandbox.profiles import get_profile


class ConfigError(Exception):
    pass


@dataclass
class MountSpec:
    src: str
    dest: str

    def __post_init__(self) -> None:
        if not Path(self.src).exists():
            raise ConfigError(f"Mount source path does not exist: {self.src}")


@dataclass
class CopySpec:
    src: str
    dest: str

    def __post_init__(self) -> None:
        if not Path(self.src).exists():
            raise ConfigError(f"Copy source path does not exist: {self.src}")


@dataclass
class MountsConfig:
    inputs: list[MountSpec] = field(default_factory=list)
    environment: list[MountSpec] = field(default_factory=list)


@dataclass
class SetupConfig:
    copy: list[CopySpec] = field(default_factory=list)


@dataclass
class ResourcesConfig:
    cpus: int = 4
    mem_gb: int = 16
    time: str = "02:00:00"
    gpu: int = 0
    partition: str = "general"


@dataclass
class DepsConfig:
    conda_env: Optional[str] = None
    pip_requirements: Optional[str] = None


@dataclass
class TaskConfig:
    task_id: str
    image: str
    mounts: MountsConfig
    resources: ResourcesConfig
    setup: SetupConfig = field(default_factory=SetupConfig)
    deps: DepsConfig = field(default_factory=DepsConfig)
    network: bool = True
    entrypoint: str = "claude"
    prompt: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> TaskConfig:
        if "task_id" not in data:
            raise ConfigError("Required field missing: task_id")
        if "image" not in data:
            raise ConfigError("Required field missing: image")

        profile = get_profile()

        # Add timestamp suffix + random hex to task_id
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = os.urandom(2).hex()
        task_id = f"{data['task_id']}-{timestamp}-{suffix}"

        # Parse mounts
        mounts_data = data.get("mounts", {})
        mounts = MountsConfig(
            inputs=[
                MountSpec(**m) for m in mounts_data.get("inputs", [])
            ],
            environment=[
                MountSpec(**m) for m in mounts_data.get("environment", [])
            ],
        )

        # Parse setup
        setup_data = data.get("setup", {})
        setup = SetupConfig(
            copy=[CopySpec(**c) for c in setup_data.get("copy", [])]
        )

        # Parse resources with profile defaults
        res_data = data.get("resources", {})
        resources = ResourcesConfig(
            cpus=res_data.get("cpus", profile.default_cpus),
            mem_gb=res_data.get("mem_gb", profile.default_mem_gb),
            time=res_data.get("time", profile.default_time),
            gpu=res_data.get("gpu", 0),
            partition=res_data.get("partition", profile.default_partition),
        )

        # Parse deps
        deps_data = data.get("deps", {})
        deps = DepsConfig(
            conda_env=deps_data.get("conda_env"),
            pip_requirements=deps_data.get("pip_requirements"),
        )

        return cls(
            task_id=task_id,
            image=data["image"],
            mounts=mounts,
            resources=resources,
            setup=setup,
            deps=deps,
            network=data.get("network", True),
            entrypoint=data.get("entrypoint", "claude"),
            prompt=data.get("prompt"),
        )


def load_config(path: Path) -> TaskConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return TaskConfig.from_dict(data)
