# Containerizer Sandbox

Run AI coding agents (Claude Code, etc.) in isolated Apptainer containers on HPC clusters with SLURM job scheduling.

Uses a two-layer container strategy: `base-system.sif` (Ubuntu 22.04 + Python, Node.js, core tools) and `base-agent.sif` (adds Claude Code + sandbox environment).

## Get Started

Paste this into your coding agent (Claude Code, Cursor, Gemini CLI, etc.):

```
Read INSTALL.md from https://github.com/Kamaleswaran-Lab/containerizer and follow the instructions to install HPC Agent Sandbox and start running containerized agents.
```

That's it. The agent handles the rest.

## Quick Start

```bash
# Launch an interactive sandbox session
sandbox shell --task task.yaml

# SSH mode for IDE access
sandbox shell --task task.yaml --ssh

# Build container images from definitions
sandbox build

# View task audit trail
sandbox audit --task-id <id>

# Clean up old tasks
sandbox cleanup --older-than 7d

# Stop a running task
sandbox stop --task-id <id>
```

## CLI Subcommands

| Command   | Description                                      |
|-----------|--------------------------------------------------|
| `shell`   | Launch an interactive sandbox session             |
| `build`   | Build `.sif` container images from definition files |
| `audit`   | Show audit information for a completed task       |
| `cleanup` | Remove old task directories and logs              |
| `stop`    | Cancel a running sandbox SLURM job                |

## AI Agent Integration

Three skills are provided in `skills/` for AI agent integration:

- **sandbox-install** — automated setup of the sandbox CLI and dependencies
- **sandbox-configure** — interactive wizard to generate a `task.yaml`
- **sandbox-reference** — CLI command reference for day-to-day use

## Requirements

- Python 3.11+
- [Apptainer](https://apptainer.org/) container runtime
- SLURM workload manager
- [uv](https://docs.astral.sh/uv/) package manager
