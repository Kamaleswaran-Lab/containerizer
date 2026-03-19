---
name: sandbox-install
description: One-time setup for HPC Agent Sandbox — install CLI as a package, locate images, install skills into the agent
---

# Sandbox Install

Set up HPC Agent Sandbox on this system and install skills into the user's agent.

## Instructions

Follow these steps in order. Ask the user for input only where indicated. Do not skip steps.

## Step 1 — Install uv

Check if uv is available:

```bash
uv --version
```

If missing, install it — don't ask, just do it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then ensure it's on PATH (source `~/.local/bin/env` or equivalent) and verify `uv --version` works.

## Step 2 — Install the Sandbox CLI

Install the sandbox CLI as a dependency in the user's current project:

```bash
uv add hpc-agent-sandbox --git https://github.com/Kamaleswaran-Lab/containerizer.git
```

This handles Python version resolution automatically — uv will fetch Python 3.11+ if the system version is too old. No need to check Python version separately.

Verify the install:

```bash
uv run sandbox --version
```

If this fails, check `uv pip list` to confirm the package installed and troubleshoot from there.

## Step 3 — Check Apptainer

```bash
apptainer --version
```

This is the only hard prerequisite that can't be auto-installed. If missing:
- Check if it's available via `module load apptainer` or `module load singularity`
- If not available at all, tell the user: apptainer is required and must be installed by a system administrator

Also check SLURM (optional):
```bash
sinfo --version
```

If missing, note it but continue — sandbox can run without SLURM for testing.

## Step 4 — Locate Container Images

Check for `.sif` images in these locations:

1. `$SANDBOX_IMAGE_DIR` (if set)
2. `/work/$USER/sandbox/images/`
3. Common HPC paths the user might suggest

If images are found, list them. If not, ask:
- "Do you have pre-built .sif images? Where are they?"
- "Or do you need to build them? (requires root or fakeroot access)"

Note the image path for environment config.

## Step 5 — Configure Environment

Ask about two settings:

1. **Scratch path**: "Where should sandbox store task data? Default is `/work/$USER`. Must be on a shared filesystem visible to compute nodes."
2. **Image directory**: "Where are your .sif container images?" (Use the path from Step 4 if found.)

Add exports to the user's shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export SANDBOX_SCRATCH="/work/$USER"          # or their custom path
export SANDBOX_IMAGE_DIR="/path/to/images"    # where .sif files live
```

## Step 6 — Install Skills into Agent

The sandbox package includes two skills the agent needs for day-to-day use:
- **sandbox-configure** — interactive wizard to generate a `task.yaml`
- **sandbox-reference** — CLI command reference

Find the skill files. They are in the `skills/` directory of the installed package or the git repo. You can locate them via:

```bash
uv run python -c "import importlib.resources; print(importlib.resources.files('hpc_agent_sandbox'))"
```

Or fetch them directly from the repo:
- `https://github.com/Kamaleswaran-Lab/containerizer.git` → `skills/sandbox-configure/`
- `https://github.com/Kamaleswaran-Lab/containerizer.git` → `skills/sandbox-reference/`

**How to install depends on the agent platform.** Figure out what the user is running and integrate accordingly:

- **Claude Code**: Install as slash commands in `.claude/commands/` or copy skill files where the agent can reference them
- **Cursor**: Add to `.cursor/rules/` or the project's rule configuration
- **Gemini CLI**: Add to `.gemini/` context or tool configuration
- **Other agents**: Ask the user how their agent loads context/skills and install appropriately

Don't prescribe a single method — determine what makes sense for the user's setup.

## Step 7 — Verification Checklist

Run through and confirm each item:

- [ ] `uv run sandbox --version` prints a version
- [ ] `apptainer --version` works
- [ ] At least one `.sif` image is located
- [ ] `SANDBOX_SCRATCH` is set or defaults to `/work/$USER`
- [ ] Skills are installed in the agent

Report results to the user. If anything failed, help them fix it.
