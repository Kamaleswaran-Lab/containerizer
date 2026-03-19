---
name: sandbox-configure
description: Analyze current repo and generate a task.yaml configuration for HPC Agent Sandbox
---

# Sandbox Configure

Generate a `task.yaml` configuration file for HPC Agent Sandbox by **analyzing the current repo first**, then presenting a proposed config for the user to amend.

## Instructions

You are a configuration generator. Instead of asking the user a series of questions, you **inspect the repo**, **infer sensible defaults**, and **present a complete proposed config** for review. Use `references/template.yaml` (relative to this file) as the structural reference for all field names and nesting.

**Important rules:**
- Only include fields whose values differ from the defaults listed below.
- Keep the generated YAML clean — no commented-out blocks.
- Validate paths exist on the host when referencing them.
- Write the final file to the location the user specifies (default: `task.yaml` in the current directory).

## Defaults

| Field | Default |
|---|---|
| resources.cpus | 4 |
| resources.mem_gb | 16 |
| resources.time | 02:00:00 |
| resources.gpu | 0 |
| resources.partition | general |
| network | true |
| entrypoint | claude |

---

## Phase 1 — Repo Analysis (do this silently)

Inspect the repo the user invoked this skill from. Do NOT ask questions during this phase — just gather information.

### 1.1 Task ID

Derive from the repo directory name. For example, if the repo is at `/home/user/projects/my-project`, suggest `my-project` as the task ID.

### 1.2 Language & Framework Detection

Look for these files to determine the project's ecosystem:

| File | Signal |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `setup.cfg` | Python project |
| `environment.yml`, `conda.yaml` | Conda environment |
| `package.json`, `yarn.lock`, `pnpm-lock.yaml` | Node.js project |
| `Cargo.toml` | Rust project |
| `go.mod` | Go project |
| `Makefile`, `CMakeLists.txt` | C/C++ project |
| `Gemfile` | Ruby project |
| `pom.xml`, `build.gradle` | Java/JVM project |

**What to infer:**
- If `requirements.txt` exists, set `deps.pip_requirements` to install it at startup (use the container path where the repo copy will live, e.g., `/output/<repo>/requirements.txt`).
- If conda files exist, note it for environment mount suggestions.
- If ML frameworks are detected (see 1.4), adjust resource suggestions upward.

### 1.3 Data Directories

Check for directories or patterns that suggest data inputs:
- `data/`, `datasets/`, `input/`, `raw/` directories in the repo
- `.dvc` files (DVC-tracked data)
- Symlinks pointing to `/work/`, `/projects/`, or other cluster storage paths
- Large file patterns (`.csv`, `.parquet`, `.h5`, `.zarr`, `.nc`, `.npy`)

If found, consider suggesting `mounts.inputs[]` entries for any external data paths discovered via symlinks. Data directories inside the repo itself will be included automatically via the `setup.copy` of the repo.

### 1.4 GPU Signals

Search the codebase for GPU indicators:
- Python imports: `torch`, `tensorflow`, `tf`, `jax`, `cupy`, `cudf`, `pycuda`
- CUDA files: `*.cu`, `*.cuh`
- Config references: `cuda`, `gpu`, `nvidia` in config files
- ML training scripts: references to `trainer`, `accelerate`, `deepspeed`, `horovod`

**Resource inference from GPU signals:**
- No GPU signals → `gpu: 0`, `partition: general` (defaults, omit from YAML)
- Light GPU use (single torch import, inference-style code) → `gpu: 1`, `partition: gpu`, `mem_gb: 32`
- Heavy GPU use (distributed training, multiple GPU references, deepspeed/accelerate) → `gpu: 2`, `partition: gpu`, `mem_gb: 64`
- Be conservative — do NOT suggest more than 2 GPUs unless there is strong evidence

### 1.5 Repo Size & Complexity

Quickly assess:
- Approximate file count (is this a small script or a large project?)
- Presence of tests (`tests/`, `test_*.py`, `*_test.go`, `__tests__/`) — suggests a development workflow
- CI configs (`.github/workflows/`, `.gitlab-ci.yml`) — mature project
- Large files or build artifacts that might affect copy time

Use this to adjust:
- **Small projects** (< 50 files): defaults are fine
- **Medium projects** (50-500 files): `cpus: 4`, `mem_gb: 16` (defaults)
- **Large projects** (500+ files, compiled languages): consider `cpus: 8`, `mem_gb: 32`

### 1.6 Existing Config

Check if `task.yaml` already exists in the repo. If it does:
- Read it and use it as the starting point instead of generating from scratch
- Note to the user that you found an existing config and are proposing updates based on the current repo state

---

## Phase 2 — Present Proposed Config

After analysis, present the proposed `task.yaml` with reasoning. Format your response like this:

### Analysis Summary

Briefly list what you detected (2-4 bullet points). For example:
- Python project with `pyproject.toml` and `requirements.txt`
- PyTorch detected in imports — suggesting GPU resources
- `data/` directory contains symlink to `/work/user/datasets/imagenet`

### Proposed Configuration

Show the full YAML. Use inline comments to explain non-obvious choices:

```yaml
task_id: my-project
image: base-agent.sif

setup:
  copy:
    - src: /absolute/path/to/current/repo  # Copy this repo into the container workspace
      dest: /output/my-project

mounts:
  inputs:
    - src: /work/user/datasets/imagenet  # Symlink target from data/ directory
      dest: /input/imagenet

resources:
  gpu: 1          # PyTorch detected in src/train.py
  partition: gpu
  mem_gb: 32      # Increased for GPU workload

deps:
  pip_requirements: /output/my-project/requirements.txt  # Found in repo root
```

### Uncertainty Flags

If you're unsure about any setting, call it out explicitly below the YAML:
- "Detected `torch` imports — suggesting 1 GPU. Adjust if you need multi-GPU training."
- "Found `data/` symlink to `/work/user/datasets/imagenet` — assuming this should be mounted read-only. Let me know if the agent needs write access."
- "No conda environment detected. If you need one mounted, let me know the path."

**Key decisions to always include:**
- The `setup.copy` entry for the current repo (use absolute path of the current working directory as `src`, and `/output/<repo-name>` as `dest`). This is the most common use case — the user wants to work on their code inside the sandbox.
- Image choice: default to `base-agent.sif` unless the user indicated otherwise.
- Only include fields that differ from defaults.

---

## Phase 3 — User Amendment

After presenting the proposed config:

1. Ask: **"Want me to adjust anything, or should I write this to `task.yaml`?"**
2. If the user requests changes, apply them and show the updated YAML.
3. Once confirmed:
   - Read `references/template.yaml` to validate field structure.
   - Write the final file to the agreed location (default: `task.yaml` in the current directory).
   - Confirm the file was written.

---

## Example: Minimal Python Project

For a small Python repo at `/home/user/projects/data-analysis` with just a `requirements.txt`:

```yaml
task_id: data-analysis
image: base-agent.sif

setup:
  copy:
    - src: /home/user/projects/data-analysis
      dest: /output/data-analysis

deps:
  pip_requirements: /output/data-analysis/requirements.txt
```

## Example: ML Training Project

For a PyTorch training repo at `/home/user/projects/model-training` with `requirements.txt`, torch imports, and a symlink `data/ -> /work/user/datasets/coco`:

```yaml
task_id: model-training
image: base-agent.sif

setup:
  copy:
    - src: /home/user/projects/model-training
      dest: /output/model-training

mounts:
  inputs:
    - src: /work/user/datasets/coco
      dest: /input/coco

resources:
  gpu: 1
  partition: gpu
  mem_gb: 32
  time: "04:00:00"

deps:
  pip_requirements: /output/model-training/requirements.txt
```

## Example: Simple Script (no deps)

For a tiny repo at `/home/user/projects/hello-world` with just a few Python files and no `requirements.txt`:

```yaml
task_id: hello-world
image: base-agent.sif

setup:
  copy:
    - src: /home/user/projects/hello-world
      dest: /output/hello-world
```
