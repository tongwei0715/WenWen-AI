"""`wenwen update` — self-upgrade from the WenWen AI fork's GitHub releases."""

from __future__ import annotations

import click

from octop.cli.support.db import resolve_cli_locale
from octop.infra.setup.self_update import (
    fetch_fork_release,
    get_editable_path,
    get_source_dir,
    get_wenwen_repo,
    get_wenwen_version,
    is_newer_wenwen,
    is_source_install,
    resolve_venv_python,
    run_upgrade,
)


@click.command("update")
@click.option("--check", is_flag=True, default=False, help="Only check, do not install.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose installer output.")
@click.option(
    "--allow-prerelease",
    "allow_prerelease",
    is_flag=True,
    default=False,
    help="Include and allow installing pre-releases (alpha / beta / rc / dev).",
)
def update(check: bool, yes: bool, verbose: bool, allow_prerelease: bool) -> None:
    """Check for and install a newer WenWen AI release."""
    current = get_wenwen_version()
    tag, _html_url, _body = fetch_fork_release()
    click.echo(f"installed: {current}")
    if tag is None:
        click.echo(
            f"could not reach the release feed for {get_wenwen_repo()} — "
            "check your network or proxy settings and retry",
            err=True,
        )
        raise SystemExit(1)
    latest = tag.lstrip("vV")
    click.echo(f"latest:    {latest}")
    if not is_newer_wenwen(latest, current):
        click.echo("already up to date")
        return
    if check:
        return

    if is_source_install():
        src_dir = get_source_dir() or get_editable_path()
        click.echo(
            f"This installation is running from source ({src_dir}).",
            err=True,
        )
        click.echo(f"To upgrade: cd {src_dir} && git pull", err=True)
        raise SystemExit(1)

    if not yes:
        click.confirm(f"Upgrade wenwen from {current} to {latest}?", abort=True)

    venv_python = resolve_venv_python()
    click.echo(f"target python: {venv_python}")
    result = run_upgrade(
        verbose=verbose,
        allow_prerelease=allow_prerelease,
        version=latest,
        locale=resolve_cli_locale(),
    )
    if not result.success:
        click.echo(f"upgrade failed: {result.error}", err=True)
        for err in result.mirror_errors:
            click.echo(f"  {err}", err=True)
        raise SystemExit(1)

    click.echo(result.message or "upgrade complete")
    if result.installed_version:
        click.echo(f"installed: {result.installed_version}")
