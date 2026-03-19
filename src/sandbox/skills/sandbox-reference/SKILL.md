---
name: sandbox-reference
description: CLI command reference for HPC Agent Sandbox — all commands, flags, and key concepts
---

# Sandbox CLI Reference

Quick reference for the `sandbox` CLI. Commands are invoked via `sandbox <command>` (installed via `uv tool install`).

## Commands at a Glance

| Command | Description |
|---|---|
| `sandbox shell` | Launch an interactive sandbox session in a container |
| `sandbox build` | Build .sif container images from definition files |
| `sandbox audit` | Show audit info (metadata + file manifest) for a completed task |
| `sandbox cleanup` | Remove old task directories, logs, and IDE cache |
| `sandbox stop` | Cancel a running sandbox task's SLURM job |
| `sandbox install-skills` | Install skills into your agent platform |
| `sandbox doctor` | Check sandbox environment health |

---

## sandbox shell

Launch an interactive container session. This is the primary command.

### Flags

| Flag | Type | Required | Description |
|---|---|---|---|
| `--task` | PATH | Yes | Path to task YAML config file |
| `--no-agent` | flag | No | Drop into plain bash instead of the configured entrypoint |
| `--new-alloc` | flag | No | Force a new SLURM allocation even if already on a compute node |
| `--ssh` | flag | No | Start an SSH server for IDE remote access instead of interactive shell |
| `--port` | INT | No | SSH port (auto-selected if omitted) |

### What Happens on Run

1. Loads and validates `task.yaml`
2. Creates task directory: `<scratch>/sandbox/tasks/<task_id>-<timestamp>-<hex>/`
3. Creates `output/` and `logs/` subdirectories
4. Runs `setup.copy` operations (copies files into `output/`)
5. Saves config snapshot to `logs/task.yaml`
6. Detects SLURM context:
   - **On compute node** — runs `apptainer exec` directly
   - **On login node** — wraps command with `srun` for allocation
7. After exit: generates `manifest.txt` (SHA-256 checksums) and `meta.json` in `logs/`

### Container Filesystem Layout

| Path | Contents | Writable |
|---|---|---|
| `/home/sandbox` | Container home directory | Yes |
| `/output` | Task output directory (persists after exit) | Yes |
| `/input/<name>` | Mounted input data directories | No |
| `/opt/conda/envs/<name>` | Mounted conda environments | No |

---

## sandbox build

Build `.sif` container images from Apptainer definition files.

### Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--image` | choice | `all` | Which image to build: `base-system`, `base-agent`, or `all` |
| `--force` | flag | No | Rebuild even if the `.sif` file already exists |
| `--def-dir` | PATH | `definitions` | Directory containing `.def` definition files |

### Images

| Image | Contents |
|---|---|
| `base-system.sif` | Ubuntu 22.04 + development tools |
| `base-agent.sif` | base-system + Claude Code + agent environment |

---

## sandbox audit

Display audit information for a completed task.

### Flags

| Flag | Type | Required | Description |
|---|---|---|---|
| `--task-id` | TEXT | Yes | Task ID to inspect (supports prefix matching) |

### Output

- **Metadata** (`meta.json`): task ID, exit code, start/end timestamps, node name, SLURM job ID
- **Manifest** (`manifest.txt`): SHA-256 checksums of all files in the output directory

---

## sandbox cleanup

Remove old task directories and associated data.

### Flags

| Flag | Type | Description |
|---|---|---|
| `--older-than` | TEXT | Remove tasks older than a duration (e.g., `7d`, `24h`) |
| `--task-id` | TEXT | Remove a specific task (supports prefix matching) |
| `--dry-run` | flag | Show what would be removed without deleting |
| `--ide-cache` | flag | Also clear the IDE server cache directory |

Must specify either `--older-than` or `--task-id`.

---

## sandbox stop

Stop a running sandbox task by cancelling its SLURM job.

### Flags

| Flag | Type | Required | Description |
|---|---|---|---|
| `--task-id` | TEXT | Yes | Task ID to stop (supports prefix matching via job name) |

Uses `scancel` to cancel the associated SLURM job.

---

## sandbox install-skills

Install sandbox skills (slash commands) into your agent platform's directory.

### Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--platform` | choice | auto-detect | Target platform: `claude`, `cursor`, `gemini`, or `generic` |
| `--global` | flag | No | Install to user-level directory instead of project |

### Platform Targets

| Platform | Project | Global |
|---|---|---|
| Claude Code | `.claude/commands/` | `~/.claude/commands/` |
| Cursor | `.cursor/rules/` | `~/.cursor/rules/` |
| Gemini CLI | `.gemini/` | `~/.gemini/` |
| Generic | `./skills/` | `./skills/` |

---

## sandbox doctor

Quick health check for the sandbox environment.

### Checks

| Check | Pass | Fail |
|---|---|---|
| `apptainer --version` | Shows version | Suggests `module load apptainer` |
| `sinfo --version` | Shows version | Warns (optional) |
| Image directory | Lists `.sif` files | Shows configured path |
| Scratch path writable | OK | Suggests `SANDBOX_SCRATCH` |

---

## Key Concepts

### Task IDs
Every task gets a unique ID: `<name>-<YYYYMMDD>-<HHMMSS>-<4hex>`. The base name comes from `task_id` in your config; the timestamp and random suffix are appended automatically.

### SLURM Context Detection
The CLI detects where it's running:
- **Compute node** (`SLURM_JOB_ID` set, no `--new-alloc`): runs container directly
- **Login node** or **`--new-alloc`**: wraps the command with `srun` to get a SLURM allocation

### SSH Mode
Use `--ssh` to start an SSH server inside the container instead of an interactive shell. This lets you connect from an IDE (VS Code, Cursor) via SSH remote. The port is auto-selected or set with `--port`.

### Container Isolation
Containers run with `--containall --cleanenv`:
- No host filesystem access except explicit bind mounts
- No host environment variables leak in
- Home directory is `/home/sandbox` (not your host home)
- DNS (`/etc/resolv.conf`) is always mounted for network access

### Scratch Path
Task directories and IDE cache live under `<scratch>/sandbox/`:
- Default scratch: `/work/$USER`
- Override with `SANDBOX_SCRATCH` environment variable
- Default image directory: `/hpc/group/kamaleswaranlab/.images/containerizer`
- Override with `SANDBOX_IMAGE_DIR` environment variable
