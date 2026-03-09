import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box
from blaqliq.api_client import BlaqLiqClient, APIError

console = Console()


@click.group()
def ai():
    """AI-powered scenario commands."""
    pass


@ai.command("generate")
@click.argument("prompt")
@click.option("--difficulty", default="beginner", type=click.Choice(["beginner", "intermediate", "advanced", "expert"]))
@click.option("--tags", default="", help="Comma-separated tags (e.g. web,sqli)")
@click.option("--wargame", is_flag=True, help="Include war games detection config")
@click.option("--api-key", default=None, help="Gemini API key (overrides stored key)")
@click.option("--start", is_flag=True, help="Immediately start a session with generated scenario")
def generate(prompt, difficulty, tags, wargame, api_key, start):
    """Generate a scenario using Gemini AI.

    Example: blaqliq ai generate "PHP app with SQL injection and weak creds"
    """
    client = BlaqLiqClient()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    with console.status("[bold]Generating scenario with Gemini...[/bold]"):
        try:
            result = client.generate_scenario(
                prompt=prompt,
                difficulty=difficulty,
                tags=tag_list,
                wargame=wargame,
                api_key=api_key,
            )
        except APIError as e:
            console.print(f"[red]✗[/red] Generation failed: {e}")
            raise SystemExit(1)

    console.print(f"[green]✓[/green] Scenario generated: [bold]{result['name']}[/bold]")
    console.print(f"   ID: [cyan]{result['scenario_id']}[/cyan]")
    console.print(f"   Difficulty: {result['difficulty']}")
    console.print(f"   Tags: {', '.join(result.get('tags', []))}")
    console.print(f"   Wargame: {'yes' if result.get('wargame_enabled') else 'no'}")

    if result.get("yaml_preview"):
        yaml_panel = Syntax(result["yaml_preview"], "yaml", theme="monokai", line_numbers=False)
        console.print(Panel(yaml_panel, title="YAML Preview", box=box.ROUNDED))

    if start:
        console.print(f"\n[bold]Starting session...[/bold]")
        try:
            session = client.start_session(result["scenario_id"], wargame=wargame)
            console.print(f"[green]✓[/green] Session started: {session['id']}")
        except APIError as e:
            console.print(f"[red]✗[/red] Failed to start session: {e}")


@ai.command("blackbox")
@click.option("--novel", is_flag=True, help="Generate a novel scenario instead of picking existing")
def blackbox(novel):
    """Start a blackbox session with a hidden target.

    Target info is hidden — you must discover it via nmap.
    Run 'blaqliq ai reveal <session_id>' after stopping to see what it was.
    """
    client = BlaqLiqClient()

    with console.status("[bold]Starting blackbox session...[/bold]"):
        try:
            result = client.start_blackbox(novel=novel)
        except APIError as e:
            console.print(f"[red]✗[/red] {e}")
            raise SystemExit(1)

    panel_content = f"""[bold]Session ID:[/bold] {result['session_id']}
[bold]Status:[/bold] [green]{result['status']}[/green]

[bold yellow]{result['message']}[/bold yellow]

[dim]The target is hidden. Discover it with:[/dim]
  docker exec -it blaqliq-attacker-{result['session_id'][:8]} nmap -sn 10.100.0.0/16

[dim]To reveal after stopping:[/dim]
  blaqliq ai reveal {result['session_id']}"""

    console.print(Panel(panel_content, title="[bold]Blackbox Session[/bold]", box=box.ROUNDED))


@ai.command("reveal")
@click.argument("session_id")
def reveal(session_id):
    """Reveal the target for a blackbox session (after stopping)."""
    client = BlaqLiqClient()
    try:
        result = client.reveal_blackbox(session_id)
    except APIError as e:
        console.print(f"[red]✗[/red] {e}")
        raise SystemExit(1)

    targets_str = "\n".join(
        f"  • {t['id']} ({t['image']})" for t in result.get("targets", [])
    )
    objectives_str = "\n".join(
        f"  • {o['id']}: {o['validation']['value']}" for o in result.get("objectives", [])
    )
    flags_str = ", ".join(result.get("flags_captured", [])) or "none"

    content = f"""[bold]Scenario:[/bold] {result['scenario_name']} ({result['scenario_id']})
[bold]Difficulty:[/bold] {result['difficulty']}

[bold]Targets:[/bold]
{targets_str}

[bold]Objectives & Flags:[/bold]
{objectives_str}

[bold]Flags You Captured:[/bold] {flags_str}"""

    console.print(Panel(content, title="[bold]Blackbox Reveal[/bold]", box=box.ROUNDED))
