from __future__ import annotations

import pytest
from pathlib import Path

from sandbox.config import TaskConfig, load_config, ConfigError


class TestConfigParsing:
    def test_valid_config_parses(self, minimal_config: dict, tmp_path: Path) -> None:
        config = TaskConfig.from_dict(minimal_config)
        assert config.task_id.startswith("test-task-")
        assert config.image == "base-agent.sif"
        assert len(config.mounts.inputs) == 1
        assert config.resources.cpus == 2

    def test_task_id_gets_timestamp_suffix(self, minimal_config: dict) -> None:
        config = TaskConfig.from_dict(minimal_config)
        assert config.task_id.startswith("test-task-")
        assert len(config.task_id) > len("test-task-")

    def test_missing_task_id_raises(self, minimal_config: dict) -> None:
        del minimal_config["task_id"]
        with pytest.raises(ConfigError, match="task_id"):
            TaskConfig.from_dict(minimal_config)

    def test_missing_image_raises(self, minimal_config: dict) -> None:
        del minimal_config["image"]
        with pytest.raises(ConfigError, match="image"):
            TaskConfig.from_dict(minimal_config)

    def test_nonexistent_input_path_raises(self, minimal_config: dict) -> None:
        minimal_config["mounts"]["inputs"][0]["src"] = "/nonexistent/path"
        with pytest.raises(ConfigError, match="does not exist"):
            TaskConfig.from_dict(minimal_config)

    def test_nonexistent_copy_src_raises(self, minimal_config: dict, tmp_path: Path) -> None:
        minimal_config["setup"] = {
            "copy": [{"src": "/nonexistent/repo", "dest": "/output/repo"}]
        }
        with pytest.raises(ConfigError, match="does not exist"):
            TaskConfig.from_dict(minimal_config)

    def test_defaults_applied(self, minimal_config: dict) -> None:
        del minimal_config["resources"]
        config = TaskConfig.from_dict(minimal_config)
        assert config.resources.cpus == 4
        assert config.resources.time == "02:00:00"

    def test_environment_mounts_readonly(self, minimal_config: dict, tmp_path: Path) -> None:
        env_dir = tmp_path / "envs" / "ml"
        env_dir.mkdir(parents=True)
        minimal_config["mounts"]["environment"] = [
            {"src": str(env_dir), "dest": "/opt/conda/envs/ml"}
        ]
        config = TaskConfig.from_dict(minimal_config)
        assert len(config.mounts.environment) == 1


class TestConfigFromFile:
    def test_load_yaml_file(self, tmp_path: Path, tmp_input_dir: Path) -> None:
        cfg_file = tmp_path / "task.yaml"
        cfg_file.write_text(f"""
task_id: file-task
image: base-agent.sif
mounts:
  inputs:
    - src: {tmp_input_dir}
      dest: /input/data
""")
        config = load_config(cfg_file)
        assert config.task_id.startswith("file-task-")

    def test_nonexistent_config_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/task.yaml"))
