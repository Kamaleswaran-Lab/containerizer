---
name: sandbox-configure
description: Interactive wizard to generate a task.yaml configuration for HPC Agent Sandbox
---

# Sandbox Configure

Generate a `task.yaml` configuration file for HPC Agent Sandbox by walking the user through each setting interactively.

## Instructions

You are a configuration wizard. Ask the user questions **one category at a time**, confirm their answers, then generate the final YAML. Use `references/template.yaml` (relative to this file) as the structural reference for all field names and nesting.

**Important rules:**
- Only include fields whose values differ from the defaults listed below.
- Keep the generated YAML clean — no commented-out blocks.
- Validate paths exist on the host when the user provides them.
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

## Wizard Flow

### Step 1 — Required Fields

Ask:
1. **Task ID** — a short name for this task (lowercase, hyphens ok). Examples: `data-analysis`, `model-training`, `code-review`.
2. **Container image** — which image to use:
   - `base-agent.sif` — includes Claude Code, ready for AI agent work (default)
   - `base-system.sif` — dev tools only, no agent pre-installed

### Step 2 — Data Mounts (read-only inputs)

Ask: "Do you have data directories the agent needs to **read** inside the container?"

If yes, for each directory ask:
- **Host path**: the absolute path on the cluster (e.g., `/work/user/data/dataset1`)
- **Container path**: where it appears inside the container (suggest `/input/<dirname>` as default)

These become `mounts.inputs[]` entries with `src` and `dest`.

### Step 3 — Environment Mounts

Ask: "Do you have conda environments or shared Python packages to mount into the container?"

If yes, for each:
- **Host path**: e.g., `/work/user/conda/envs/myenv`
- **Container path**: suggest `/opt/conda/envs/<name>`

Then ask: "Which environment should be auto-activated at startup?" This sets `deps.conda_env`.

These become `mounts.environment[]` entries.

### Step 4 — Workspace Setup (writable copies)

Ask: "Do you have code or repos to **copy** into the workspace? The agent will work on the copy, leaving originals untouched."

If yes, for each:
- **Host path**: source directory to copy
- **Container path**: destination inside `/output/` (suggest `/output/<dirname>`)

These become `setup.copy[]` entries.

### Step 5 — SLURM Resources

Show the defaults and ask: "Do you need to change any resource settings?"

If yes, ask about each:
- CPUs (default 4)
- Memory in GB (default 16)
- Wall time as HH:MM:SS (default 02:00:00)
- GPUs (default 0) — if >0, suggest changing partition to `gpu`
- Partition (default `general`)

### Step 6 — Optional Settings

Ask about each only if relevant:
- **Network access**: default is enabled. Ask only: "Do you need to disable network access?"
- **Entrypoint**: default is `claude`. Ask: "What should run when the container starts?" Options: `claude` (default), `bash`, or a custom command.
- **Prompt**: for batch mode. Ask: "Do you want to pass a prompt to the agent? (Leave blank for interactive mode)"
- **pip requirements**: Ask: "Do you have a requirements.txt to install at startup?"

### Step 7 — Generate

1. Read `references/template.yaml` to confirm field structure.
2. Build the YAML with only non-default values included.
3. Show the generated YAML to the user for review.
4. Ask where to save it (default: `task.yaml` in the current directory).
5. Write the file.

## Example Output (minimal)

```yaml
task_id: data-analysis
image: base-agent.sif
```

## Example Output (with options)

```yaml
task_id: model-training
image: base-agent.sif

mounts:
  inputs:
    - src: /work/jdoe/data/imagenet
      dest: /input/imagenet
  environment:
    - src: /work/jdoe/conda/envs/torch
      dest: /opt/conda/envs/torch

setup:
  copy:
    - src: /home/jdoe/projects/trainer
      dest: /output/trainer

resources:
  gpu: 2
  partition: gpu
  mem_gb: 32
  time: "08:00:00"

deps:
  conda_env: torch
```
