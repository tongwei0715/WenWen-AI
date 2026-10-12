"""wenwen version command."""

from __future__ import annotations

import click


@click.command("version")
def version() -> None:
    """Show the installed wenwen version."""
    try:
        from importlib.metadata import version as _v

        v = _v("wenwen-ai")
    except Exception:
        v = "unknown"
    click.echo(f"wenwen v{v}")
