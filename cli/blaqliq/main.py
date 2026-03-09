import click
from rich.console import Console
from blaqliq.commands.auth import auth
from blaqliq.commands.session import session
from blaqliq.commands.wargame import wargame
from blaqliq.commands.ai import ai

console = Console()

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    BlaqLiq - Docker Security Lab Platform

    Spin up vulnerable containers, attack them, and level up your pentesting skills.

    Quick start:
      blaqliq auth login
      blaqliq session list
      blaqliq session start dvwa-beginner
    """
    pass


cli.add_command(auth)
cli.add_command(session)
cli.add_command(wargame)
cli.add_command(ai)


# Convenience aliases at top level
@cli.command("start")
@click.argument("scenario_id")
@click.option("--wargame", is_flag=True)
@click.option("--blackbox", is_flag=True)
def start_alias(scenario_id, wargame, blackbox):
    """Shortcut for 'blaqliq session start'."""
    from blaqliq.api_client import BlaqLiqClient, APIError
    from rich.panel import Panel
    from rich import box

    client = BlaqLiqClient()
    with console.status(f"[bold]Starting {scenario_id}...[/bold]"):
        try:
            result = client.start_session(scenario_id, wargame=wargame, blackbox=blackbox)
        except APIError as e:
            console.print(f"[red]✗[/red] {e}")
            raise SystemExit(1)

    console.print(f"[green]✓[/green] Session started: [bold]{result['id']}[/bold]")
    console.print(f"[dim]Attacker: docker exec -it blaqliq-attacker-{result['id'][:8]} bash[/dim]")


@cli.command("stop")
@click.argument("session_id")
def stop_alias(session_id):
    """Shortcut for 'blaqliq session stop'."""
    from blaqliq.api_client import BlaqLiqClient, APIError
    client = BlaqLiqClient()
    with console.status(f"[bold]Stopping...[/bold]"):
        try:
            client.stop_session(session_id)
        except APIError as e:
            console.print(f"[red]✗[/red] {e}")
            raise SystemExit(1)
    console.print(f"[green]✓[/green] Stopped")


if __name__ == "__main__":
    cli()
