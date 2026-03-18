# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HPC Agent Sandbox — a CLI tool (`sandbox`) that runs AI coding agents in isolated Apptainer containers on HPC clusters with SLURM job scheduling. Uses a two-layer container strategy: `base-system.sif` (OS + tools) and `base-agent.sif` (Claude Code + environment).

## Commands

```bash
# Install dependencies
uv sync --dev

# Run unit tests (no container runtime needed)
uv run pytest tests/ --ignore=tests/integration -v

# Run a single test
uv run pytest tests/test_config.py::TestConfigParsing::test_valid_config_parses -v

# Run integration tests (requires apptainer + .sif image)
uv run pytest tests/integration/ -m integration -v

# CLI usage
uv run sandbox --version
uv run sandbox shell --help
uv run sandbox build --help
```

Always use `uv run` to invoke commands — never `source .venv/bin/activate`.

## Architecture

**CLI layer** (`cli.py`): Click-based entry point with 5 subcommands: `shell`, `build`, `audit`, `cleanup`, `stop`. The `shell` command is the primary flow — it loads config, creates task directories, detects SLURM context, and dispatches to either direct apptainer exec or srun-wrapped execution.

**Config pipeline** (`config.py` → `container.py`): YAML task configs are parsed into `TaskConfig` dataclasses with validation in `__post_init__`. `build_apptainer_cmd()` translates a `TaskConfig` into a full `apptainer exec --containall --cleanenv` command list with bind mounts, env vars, and GPU flags.

**SLURM integration** (`slurm.py`): `SlurmContext` enum (LOGIN_NODE, COMPUTE_NODE, NEEDS_ALLOCATION) drives whether the container runs directly or via `srun`. Detection is based on `SLURM_JOB_ID` env var + `force_new_alloc` flag.

**SSH mode** (`ssh.py`): Alternative entry path where the container runs `sshd` instead of an interactive shell. Generates host keys and `sshd_config` on the host side, but all config paths reference container mount points (`/run/sshd/...`) since sshd reads them inside the container.

**Profiles** (`profiles/`): `DefaultProfile` frozen dataclass controls paths (scratch, images, tasks, IDE cache). Paths are configurable via `SANDBOX_SCRATCH` and `SANDBOX_IMAGE_DIR` env vars, defaulting to `/work/$USER/sandbox/`.

**Post-run audit** (`audit.py`): `generate_manifest()` produces SHA-256 checksums of all output files; `generate_metadata()` writes `meta.json` with task ID, exit code, timestamps, node, and SLURM job ID.

## Key Design Constraints

- **Container paths vs host paths**: Apptainer `--containall` means the container filesystem is isolated. Config files, keys, and PIDs written to the host's sshd directory are accessed inside the container at `/run/sshd/`. The container home is always `/home/sandbox` (set via `--home` flag).
- **Mount security model**: Inputs are `:ro`, outputs are `:rw`, environment mounts are `:ro`. DNS (`/etc/resolv.conf`) is always mounted. `.claude` auth dir is mounted read-write to container home.
- **Task IDs**: Auto-suffixed with `YYYYMMDD-HHMMSS-XXXX` (4 random hex chars) to prevent collisions.
- **Scratch path**: `/work/<userid>` on this cluster, not `/tmp` or home directory.

## Testing Approach

Unit tests mock no external dependencies — they test config parsing, command building, and utility functions in-process. Integration tests (marked `@pytest.mark.integration`) require a real `apptainer` binary and `.sif` image; they run actual containers and verify isolation, mounts, and network behavior. The `run_in_container()` helper in `tests/integration/conftest.py` wraps `apptainer exec` calls.

## JaRVIS

Use `/jarvis-reload` to reload context mid-session if needed.
After completing any meaningful task, run `/jarvis-reflect` to capture what you learned.
