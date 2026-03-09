import click
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich import box
from blaqliq.api_client import BlaqLiqClient, APIError

console = Console()

LEVEL_COLORS = {
    "clean": "green",
    "warning": "yellow",
    "detected": "bold orange1",
    "busted": "bold red",
}

LEVEL_ICONS = {
    "clean": "●",
    "warning": "⚠",
    "detected": "🚨",
    "busted": "💀",
}


def render_stealth_meter(state: dict) -> Panel:
    level = state["detection_level"]
    score = state["detection_score"]
    active = state["is_active"]
    color = LEVEL_COLORS.get(level, "white")
    icon = LEVEL_ICONS.get(level, "?")

    # Score bar (0-100)
    bar_filled = min(score, 100)
    bar_empty = 100 - bar_filled
    bar = f"[{color}]{'█' * (bar_filled // 5)}[/{color}][dim]{'░' * (bar_empty // 5)}[/dim]"

    status_line = f"[bold]{icon} Detection Level:[/bold] [{color}]{level.upper()}[/{color}]"
    score_line = f"[bold]Score:[/bold] {score}/100"

    thresholds = "Thresholds: [green]CLEAN<10[/green] | [yellow]WARNING≥10[/yellow] | [orange1]DETECTED≥40[/orange1] | [red]BUSTED≥100[/red]"

    active_str = "[green]ACTIVE[/green]" if active else "[dim]INACTIVE[/dim]"

    content = f"{status_line}\n{score_line}\n{bar}\n{thresholds}\n\n[bold]State:[/bold] {active_str}"

    if state.get("busted_at"):
        content += f"\n[red]BUSTED at {state['busted_at']}[/red]"

    title_color = color
    return Panel(content, title=f"[{title_color}]War Games Detection Meter[/{title_color}]", box=box.ROUNDED)


@click.group()
def wargame():
    """War games commands."""
    pass


@wargame.command("status")
@click.argument("session_id")
@click.option("--watch", is_flag=True, help="Live-refresh every 5 seconds")
def wargame_status(session_id, watch):
    """Show war games detection status for SESSION_ID."""
    client = BlaqLiqClient()

    if not watch:
        try:
            state = client.get_wargame(session_id)
            console.print(render_stealth_meter(state))

            # Show recent events
            events = client.get_wargame_events(session_id, limit=10)
            if events:
                _print_events_table(events)
        except APIError as e:
            console.print(f"[red]✗[/red] {e}")
            raise SystemExit(1)
    else:
        # Live watch mode
        console.print(f"[dim]Watching session {session_id[:8]}... Press Ctrl+C to stop[/dim]\n")
        try:
            with Live(console=console, refresh_per_second=0.2) as live:
                while True:
                    try:
                        state = client.get_wargame(session_id)
                        live.update(render_stealth_meter(state))

                        if not state["is_active"]:
                            console.print("\n[dim]Game over.[/dim]")
                            break
                    except APIError as e:
                        live.update(f"[red]Error: {e}[/red]")

                    time.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped watching[/dim]")


def _print_events_table(events: list):
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Time", width=20)
    table.add_column("Type", width=15)
    table.add_column("Severity", width=12)
    table.add_column("Score +", justify="right", width=8)
    table.add_column("Source IP", width=15)

    SEVERITY_COLORS = {"warning": "yellow", "detected": "orange1", "busted": "red"}

    for e in events:
        sev_color = SEVERITY_COLORS.get(e["severity"], "white")
        table.add_row(
            e["timestamp"][:19] if e.get("timestamp") else "",
            e["event_type"],
            f"[{sev_color}]{e['severity']}[/{sev_color}]",
            f"+{e['score_delta']}",
            e.get("source_ip") or "[dim]unknown[/dim]",
        )

    console.print(Panel(table, title="Recent Detection Events", box=box.ROUNDED))
