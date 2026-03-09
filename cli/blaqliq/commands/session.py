import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from blaqliq.api_client import BlaqLiqClient, APIError

console = Console()

STATUS_COLORS = {
    "running": "green",
    "starting": "yellow",
    "stopping": "yellow",
    "stopped": "dim",
    "error": "red",
}


@click.group()
def session():
    """Lab session commands."""
    pass


@session.command("start")
@click.argument("scenario_id")
@click.option("--wargame", is_flag=True, help="Enable war games detection mode")
@click.option("--blackbox", is_flag=True, help="Enable blackbox mode (hidden target)")
@click.option("--kali", is_flag=True, help="Use Kali Linux attacker (pro+)")
def start_session(scenario_id, wargame, blackbox, kali):
    """Start a lab session for SCENARIO_ID."""
    client = BlaqLiqClient()

    mode_str = " [war games]" if wargame else ""
    bb_str = " [blackbox]" if blackbox else ""

    with console.status(f"[bold]Starting session: {scenario_id}{mode_str}{bb_str}...[/bold]"):
        try:
            result = client.start_session(scenario_id, wargame=wargame, blackbox=blackbox)
        except APIError as e:
            console.print(f"[red]✗[/red] Failed to start session: {e}")
            raise SystemExit(1)

    status_color = STATUS_COLORS.get(result["status"], "white")

    panel_content = f"""[bold]Session ID:[/bold] {result['id']}
[bold]Status:[/bold] [{status_color}]{result['status']}[/{status_color}]
[bold]Mode:[/bold] {result['mode']}
[bold]Network:[/bold] {result.get('docker_network_name', 'N/A')}
[bold]Containers:[/bold] {result.get('container_count', 0)}"""

    if not blackbox and result.get("scenario_id"):
        panel_content += f"\n[bold]Scenario:[/bold] {result['scenario_id']}"

    if blackbox:
        panel_content += "\n[bold yellow]Target is hidden. Use nmap to discover.[/bold yellow]"

    console.print(Panel(panel_content, title="[bold green]Session Started[/bold green]", box=box.ROUNDED))
    console.print(f"\n[dim]To connect to attacker: docker exec -it blaqliq-attacker-{result['id'][:8]} bash[/dim]")
    console.print(f"[dim]To stop: blaqliq session stop {result['id']}[/dim]")


@session.command("stop")
@click.argument("session_id")
def stop_session(session_id):
    """Stop a running session."""
    client = BlaqLiqClient()

    with console.status(f"[bold]Stopping session {session_id[:8]}...[/bold]"):
        try:
            result = client.stop_session(session_id)
        except APIError as e:
            console.print(f"[red]✗[/red] Failed to stop session: {e}")
            raise SystemExit(1)

    console.print(f"[green]✓[/green] Session [bold]{session_id[:8]}[/bold] stopped")


@session.command("status")
@click.argument("session_id", required=False)
def session_status(session_id):
    """Show session status. If no ID given, lists all sessions."""
    client = BlaqLiqClient()
    try:
        if session_id:
            result = client.get_session(session_id)
            _print_session_detail(result)
        else:
            sessions = client.list_sessions()
            _print_sessions_table(sessions)
    except APIError as e:
        console.print(f"[red]✗[/red] {e}")
        raise SystemExit(1)


def _print_sessions_table(sessions: list):
    if not sessions:
        console.print("[dim]No sessions found[/dim]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Scenario", width=20)
    table.add_column("Mode", width=10)
    table.add_column("Status", width=12)
    table.add_column("Containers", justify="right")
    table.add_column("Created")

    for s in sessions:
        status = s["status"]
        color = STATUS_COLORS.get(status, "white")
        scenario = "[hidden]" if s["blackbox"] and s["status"] != "stopped" else (s.get("scenario_id") or "?")
        table.add_row(
            s["id"][:8],
            scenario,
            s["mode"],
            f"[{color}]{status}[/{color}]",
            str(s.get("container_count", 0)),
            s["created_at"][:19] if s.get("created_at") else "",
        )

    console.print(table)


def _print_session_detail(s: dict):
    status = s["status"]
    color = STATUS_COLORS.get(status, "white")
    scenario = "[hidden]" if s["blackbox"] and s["status"] != "stopped" else (s.get("scenario_id") or "?")

    content = f"""[bold]ID:[/bold]       {s['id']}
[bold]Scenario:[/bold] {scenario}
[bold]Status:[/bold]   [{color}]{status}[/{color}]
[bold]Mode:[/bold]     {s['mode']}
[bold]Blackbox:[/bold] {'yes' if s['blackbox'] else 'no'}
[bold]Network:[/bold]  {s.get('docker_network_name', 'N/A')}
[bold]Flags:[/bold]    {', '.join(s.get('flags_captured', [])) or 'none captured'}"""

    console.print(Panel(content, title=f"Session {s['id'][:8]}", box=box.ROUNDED))


@session.command("flag")
@click.argument("session_id")
@click.argument("flag_value")
@click.option("--objective", required=True, help="Objective ID to submit flag for")
def submit_flag(session_id, flag_value, objective):
    """Submit a flag for a session objective."""
    client = BlaqLiqClient()
    try:
        result = client.submit_flag(session_id, flag_value, objective)
        if result["correct"]:
            console.print(f"[green]✓[/green] {result['message']}")
        else:
            console.print(f"[red]✗[/red] {result['message']}")
    except APIError as e:
        console.print(f"[red]✗[/red] {e}")
        raise SystemExit(1)


@session.command("list")
def list_scenarios_cmd():
    """List available scenarios."""
    client = BlaqLiqClient()
    try:
        scenarios = client.list_scenarios()

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("ID", width=25)
        table.add_column("Name", width=35)
        table.add_column("Difficulty", width=14)
        table.add_column("Tags", width=20)
        table.add_column("Wargame", width=9)

        DIFF_COLORS = {"beginner": "green", "intermediate": "yellow", "advanced": "red", "expert": "bold red"}

        for s in scenarios:
            diff_color = DIFF_COLORS.get(s["difficulty"], "white")
            wg = "[green]yes[/green]" if s.get("wargame_enabled") else "[dim]no[/dim]"
            table.add_row(
                s["id"],
                s["name"],
                f"[{diff_color}]{s['difficulty']}[/{diff_color}]",
                ", ".join(s.get("tags", [])),
                wg,
            )

        console.print(table)
    except APIError as e:
        console.print(f"[red]✗[/red] {e}")
        raise SystemExit(1)
