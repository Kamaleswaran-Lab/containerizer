---
name: sandbox-install
description: One-time setup for HPC Agent Sandbox — check apptainer, locate images, configure environment, verify installation
---

# Sandbox Install

Complete setup for HPC Agent Sandbox. This skill assumes the sandbox CLI and skills are already installed (via INSTALL.md). It handles the remaining system configuration.

## Instructions

Follow these steps in order. Ask the user for input only where indicated. Do not skip steps.

## Step 1 — Check Apptainer

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

## Step 2 — Locate Container Images

Check for `.sif` images in these locations:

1. `$SANDBOX_IMAGE_DIR` (if set)
2. `/hpc/group/kamaleswaranlab/.images/containerizer`
3. Common HPC paths the user might suggest

If images are found, list them. If not, ask:
- "Do you have pre-built .sif images? Where are they?"
- "Or do you need to build them? (requires root or fakeroot access)"

Note the image path for environment config.

## Step 3 — Configure Environment

Ask about two settings:

1. **Scratch path**: "Where should sandbox store task data? Default is `/work/$USER`. Must be on a shared filesystem visible to compute nodes."
2. **Image directory**: "Where are your .sif container images?" (Use the path from Step 2 if found.)

Add exports to the user's shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export SANDBOX_SCRATCH="/work/$USER"          # or their custom path
export SANDBOX_IMAGE_DIR="/path/to/images"    # where .sif files live
```

## Step 4 — Verification Checklist

Run through and confirm each item:

- [ ] `uv run sandbox --version` prints a version
- [ ] `apptainer --version` works
- [ ] At least one `.sif` image is located
- [ ] `SANDBOX_SCRATCH` is set or defaults to `/work/$USER`

Report results to the user. If anything failed, help them fix it.

## Step 5 — Demo Run

Walk the user through a test run to confirm everything works end to end:

1. Run `/sandbox-configure` to generate a test `task.yaml`
2. Launch a sandbox session:
   ```bash
   uv run sandbox shell --task task.yaml
   ```
3. Report whether the container started successfully, then clean up:
   ```bash
   uv run sandbox cleanup --older-than 0s
   ```
