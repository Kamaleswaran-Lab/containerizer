# Install HPC Agent Sandbox

Paste the following into your coding agent (Claude Code, Cursor, Gemini CLI, etc.):

---

I need to set up HPC Agent Sandbox for this project.

Read the install skill at `skills/sandbox-install/SKILL.md` from the containerizer repo (https://github.com/Kamaleswaran-Lab/containerizer.git) and follow each step to:
1. Install uv (if needed) and the sandbox CLI
2. Check apptainer availability
3. Locate container images
4. Configure environment variables
5. Install the sandbox skills into this agent

---

After installation, you'll have two skills available:
- **sandbox-configure** — interactive wizard to generate a `task.yaml`
- **sandbox-reference** — CLI command reference for day-to-day use
