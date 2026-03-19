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

Install the sandbox CLI as a dependency in the user's current project:

```bash
uv add hpc-agent-sandbox --git https://github.com/Kamaleswaran-Lab/containerizer.git
```

Verify the install:

```bash
uv run sandbox --version
```

If this fails, check `uv pip list` to confirm the package installed and troubleshoot from there.

## Step 3 — Install Skills into Agent

The sandbox package includes three skills for day-to-day use:
- **sandbox-install** — one-time setup (apptainer, images, environment)
- **sandbox-configure** — interactive wizard to generate a `task.yaml`
- **sandbox-reference** — CLI command reference

Find the skill files. They are in the `skills/` directory of the installed package. Locate them via:

```bash
uv run python -c "import importlib.resources; print(importlib.resources.files('hpc_agent_sandbox'))"
```

Or fetch them directly from the repo:
- `https://github.com/Kamaleswaran-Lab/containerizer.git` → `skills/sandbox-install/`
- `https://github.com/Kamaleswaran-Lab/containerizer.git` → `skills/sandbox-configure/`
- `https://github.com/Kamaleswaran-Lab/containerizer.git` → `skills/sandbox-reference/`

**How to install depends on the agent platform.** Figure out what the user is running and integrate accordingly:

- **Claude Code**: Install as slash commands in `.claude/commands/` or copy skill files where the agent can reference them
- **Cursor**: Add to `.cursor/rules/` or the project's rule configuration
- **Gemini CLI**: Add to `.gemini/` context or tool configuration
- **Other agents**: Ask the user how their agent loads context/skills and install appropriately

Don't prescribe a single method — determine what makes sense for the user's setup.

## Step 4 — Restart and Complete Setup

Tell the user:

> Skills are installed. **Restart your agent session** so the new skills load, then run `/sandbox-install` to complete setup (apptainer check, image location, environment config, and verification). If / commands are not supported for your system, please ask your agent to use the sandbox-install skill.

Stop here. Do not proceed further — the sandbox-install skill handles the remaining setup after restart.
