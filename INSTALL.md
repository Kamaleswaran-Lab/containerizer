# Install HPC Agent Sandbox

You are an AI coding agent. Follow these steps exactly to install HPC Agent Sandbox and set up skills for the user.

## Step 1 — Install uv

Check if uv is available:

```bash
uv --version
```

If missing, install it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then ensure it's on PATH (source `~/.local/bin/env` or equivalent) and verify `uv --version` works.

## Step 2 — Install the Sandbox CLI

Install the sandbox CLI as a standalone tool (no project context needed):

```bash
uv tool install "containerizer @ git+https://github.com/Kamaleswaran-Lab/containerizer.git"
```

Verify the install:

```bash
sandbox --version
```

If this fails, check that `~/.local/bin` is on PATH (`uv tool update-shell`) and retry.

## Step 3 — Install Skills

The sandbox package bundles three skills for day-to-day use. Install them with a single command:

```bash
sandbox install-skills
```

This auto-detects your agent platform (Claude Code, Cursor, Gemini CLI) and copies skill files to the right location. You can also specify a platform explicitly:

```bash
sandbox install-skills --platform claude
sandbox install-skills --platform cursor
sandbox install-skills --platform gemini
sandbox install-skills --platform generic   # copies to ./skills/
```

Use `--global` to install to the user-level directory instead of the current project.

## Step 4 — Restart and Complete Setup

Tell the user:

> Skills are installed. **Restart your agent session** so the new skills load, then run `/sandbox-install` to complete setup (apptainer check, image location, environment config, and verification). If / commands are not supported for your system, please ask your agent to use the sandbox-install skill.

Stop here. Do not proceed further — the sandbox-install skill handles the remaining setup after restart.
