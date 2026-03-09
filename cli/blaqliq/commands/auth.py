import click
from rich.console import Console
from rich.table import Table
from blaqliq.api_client import BlaqLiqClient, APIError
from blaqliq.config import set_token, clear_token, get_token, set_api_url

console = Console()


@click.group()
def auth():
    """Authentication commands."""
    pass


@auth.command()
@click.option("--url", default=None, help="API URL (default: http://localhost:8000)")
def login(url):
    """Login to BlaqLiq."""
    if url:
        set_api_url(url)

    username = click.prompt("Username")
    password = click.prompt("Password", hide_input=True)

    client = BlaqLiqClient()
    try:
        token = client.login(username, password)
        set_token(token)
        console.print(f"[green]✓[/green] Logged in as [bold]{username}[/bold]")
    except APIError as e:
        console.print(f"[red]✗[/red] Login failed: {e}")
        raise SystemExit(1)


@auth.command()
def logout():
    """Logout from BlaqLiq."""
    clear_token()
    console.print("[green]✓[/green] Logged out")


@auth.command()
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--gemini-key", default=None, help="Gemini API key for AI features")
def register(username, email, password, gemini_key):
    """Register a new account."""
    client = BlaqLiqClient()
    try:
        user = client.register(username, email, password)
        console.print(f"[green]✓[/green] Registered as [bold]{username}[/bold]")
        console.print("Now run: blaqliq auth login")
    except APIError as e:
        console.print(f"[red]✗[/red] Registration failed: {e}")
        raise SystemExit(1)


@auth.command()
def whoami():
    """Show current user info."""
    client = BlaqLiqClient()
    try:
        me = client.get_me()
        console.print(f"[bold]Username:[/bold] {me['username']}")
        console.print(f"[bold]Email:[/bold] {me['email']}")
        console.print(f"[bold]Plan:[/bold] {me['plan']}")
    except APIError as e:
        console.print(f"[red]✗[/red] {e}")
        raise SystemExit(1)


@auth.command("create-key")
@click.option("--label", default="cli", help="Label for the API key")
def create_api_key(label):
    """Create a new API key."""
    client = BlaqLiqClient()
    try:
        result = client.create_api_key(label)
        console.print(f"[green]✓[/green] API key created:")
        console.print(f"[bold yellow]{result['raw_key']}[/bold yellow]")
        console.print("[dim]This key will not be shown again. Store it safely.[/dim]")
    except APIError as e:
        console.print(f"[red]✗[/red] {e}")
        raise SystemExit(1)
