from __future__ import annotations

import click

from sandbox import __version__


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """HPC Agent Sandbox - run AI agents in isolated containers."""
    pass
