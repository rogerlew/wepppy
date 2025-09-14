#!/usr/bin/env python3
import typer
import subprocess
import requests
import time
import os
import shutil
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax
from rich.spinner import Spinner
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Grid
from textual.binding import Binding

# --- Configuration ---
# Maps the friendly names you use in the CLI to the actual systemd service names
# and the path for their health check endpoints.
SERVICE_CONFIG = {
    "weppcloud": {
        "systemd": "gunicorn-weppcloud.service",
        "health_path": "/weppcloud-microservices/status/health"
    },
    "rq": {
        "systemd": "rq-wepppy-worker-pool.service",
        "health_path": None  # RQ workers don't have a health endpoint
    },
    "preflight": {
        "systemd": "gunicorn-preflight.service",
        "health_path": "/weppcloud-microservices/preflight/health"
    },
    "status": {
        "systemd": "gunicorn-status.service",
        "health_path": "/weppcloud-microservices/status/health" # Assuming this is correct
    },
    "wmesque": {
        "systemd": "gunicorn-wmesque.service",
        "health_path": "/webservices/wmesque/health"
    },
    "metquery": {
        "systemd": "gunicorn-metquery.service",
        "health_path": "/webservices/metquery/health"
    },
    "elevationquery": {
        "systemd": "gunicorn-elevationquery.service",
        "health_path": "/webservices/elevationquery/health"
    },
}

# The order in which to display services in the `status` command
SERVICE_ORDER = ["weppcloud", "rq", "preflight", "status", "wmesque", "metquery", "elevationquery"]

BASE_HEALTH_URL = "https://wepp.cloud"
NFS_MOUNT_POINT = "/geodata"
NFS_MOUNT_SOURCE = "nas.rocket.net:/wepp"

# --- CLI App Initialization ---
# We use Typer's `context_settings` for a consistent help message style.
cli = typer.Typer(
    name="wctl",
    help="🚀 A modern CLI for managing and monitoring the wepp.cloud infrastructure.",
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False
)
service_cli = typer.Typer(
    name="service",
    help="Manage individual systemd services.",
    no_args_is_help=True
)
cli.add_typer(service_cli)

console = Console()

# --- Helper Functions ---

def run_command(command: list[str], sudo: bool = True) -> subprocess.CompletedProcess:
    """A helper to run shell commands, with optional sudo."""
    cmd = ["sudo"] + command if sudo else command
    return subprocess.run(cmd, capture_output=True, text=True)

def get_systemd_status(service_name: str) -> tuple[str, str]:
    """Checks if a systemd service is active and returns a status emoji and text."""
    result = run_command(["systemctl", "is-active", service_name])
    status = result.stdout.strip()
    if status == "active":
        return "✅", "[bold green]Active[/bold green]"
    elif status == "inactive":
        return "❌", "[bold yellow]Inactive[/bold yellow]"
    return "🔥", f"[bold red]{status.capitalize()}[/bold red]"

def check_health_endpoint(path: str | None) -> tuple[str, str]:
    """Checks a web endpoint and returns a status emoji and text."""
    if not path:
        return "⚪", "[dim]N/A[/dim]"
    try:
        response = requests.get(f"{BASE_HEALTH_URL}{path}", timeout=5)
        if response.ok:
            return "✅", f"[bold green]OK[/bold green] ({response.status_code})"
        return "❌", f"[bold red]FAIL[/bold red] ({response.status_code})"
    except requests.RequestException:
        return "🔥", "[bold red]ERROR[/bold red]"

def check_nfs_mount(mount_point: str, source: str) -> tuple[str, str]:
    """Checks if the specified NFS share is mounted correctly."""
    if not os.path.ismount(mount_point):
        return "❌", f"[bold red]Not Mounted[/bold red] at {mount_point}"
    
    result = run_command(["mount"], sudo=False)
    for line in result.stdout.splitlines():
        if line.startswith(source) and f" on {mount_point} " in line:
            return "✅", f"[bold green]Mounted[/bold green] ({source})"
    
    return "❓", f"[bold yellow]Mounted, but source mismatch![/bold yellow]"


# --- TUI Dashboard for `wctl monitor` ---

class MonitorPane(Static):
    """A widget for a single pane in our monitoring dashboard."""
    def __init__(self, title: str, command: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.command_str = command
        self.command = command.split()
        self.process = None

    def on_mount(self) -> None:
        """Start the subprocess when the widget is mounted."""
        self.update_content()
        self.set_interval(2, self.update_content) # Refresh every 2 seconds

    def update_content(self) -> None:
        """Execute the command and update the pane's content."""
        try:
            # For streaming logs, we use a different approach
            if "-f" in self.command:
                if not self.process or self.process.poll() is not None:
                     self.process = subprocess.Popen(
                        self.command, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True
                     )
                # This part is simplified for brevity. A full implementation
                # would use async IO to read from the process without blocking.
                # For this tool, a periodic refresh is sufficient to show recent logs.
                result = run_command(self.command[:-1] + ["-n", "20"], sudo=False)
            else:
                 # Standard command execution
                 result = subprocess.run(
                    self.command,
                    capture_output=True,
                    text=True,
                    check=False,
                    env={**os.environ, "LD_LIBRARY_PATH": ""} # For htop
                )

            output = result.stdout if result.stdout else result.stderr
            panel_content = Text(output, no_wrap=True, overflow="hidden")
            self.update(Panel(panel_content, title=self.title, border_style="cyan"))
        except Exception as e:
            self.update(Panel(f"Error executing command: {e}", title=self.title, border_style="red"))


class MonitorApp(App):
    """The Textual monitoring app."""
    CSS_PATH = None
    TITLE = "WEPP.cloud Real-time Monitor"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            MonitorPane("📈 RQ Info", "rq info --url redis://129.101.202.237:6379/9", id="rq"),
            MonitorPane("💻 System Processes (htop)", "htop -b -t", id="htop"),
            MonitorPane("✈️ Preflight Logs", f"sudo journalctl -u {SERVICE_CONFIG['preflight']['systemd']} -n 50 --no-pager", id="preflight"),
            MonitorPane("📊 Status Logs", f"sudo journalctl -u {SERVICE_CONFIG['status']['systemd']} -n 50 --no-pager", id="status"),
            id="main_grid"
        )
        yield Footer()

    def on_mount(self) -> None:
        grid = self.query_one("#main_grid")
        grid.styles.grid_size_columns = "1fr 1fr"
        grid.styles.grid_size_rows = "1fr 1fr"


# --- CLI Commands ---

@cli.command()
def monitor():
    """Launch a real-time TUI dashboard to monitor the system."""
    app = MonitorApp()
    app.run()


@cli.command()
def status():
    """
    Run a comprehensive health check on all wepp.cloud services,
    disk space, and NFS mounts.
    """
    console.print(Panel(
        "[bold cyan]wctl[/] [dim]System Status Report[/dim]",
        title="[bold green]wepp.cloud[/]",
        subtitle="[dim]Generated at {}[/dim]".format(time.strftime("%Y-%m-%d %H:%M:%S")),
        border_style="green"
    ))

    with console.status("[bold yellow]Running system checks...[/]", spinner="dots") as status_spinner:
        # 1. Service Status Table
        service_table = Table(
            title="Dependent Services",
            title_style="bold magenta",
            show_header=True,
            header_style="bold blue"
        )
        service_table.add_column("Service", style="cyan", width=18)
        service_table.add_column("Systemd Status", justify="center")
        service_table.add_column("Health Endpoint", justify="center")

        for name in SERVICE_ORDER:
            config = SERVICE_CONFIG[name]
            systemd_name = config["systemd"]
            health_path = config["health_path"]
            
            status_spinner.update(f"[bold yellow]Checking {name}...[/]")
            time.sleep(0.1) # Aesthetic delay
            
            systemd_emoji, systemd_text = get_systemd_status(systemd_name)
            health_emoji, health_text = check_health_endpoint(health_path)
            
            service_table.add_row(name.capitalize(), f"{systemd_emoji} {systemd_text}", f"{health_emoji} {health_text}")
        
        console.print(service_table)

        # 2. Filesystem Status
        status_spinner.update("[bold yellow]Checking filesystems...[/]")
        time.sleep(0.2)
        
        nfs_emoji, nfs_text = check_nfs_mount(NFS_MOUNT_POINT, NFS_MOUNT_SOURCE)
        disk_result = run_command(["df", "-h"], sudo=False)
        
        # We'll create a panel to group these together
        fs_panel_content = f"{nfs_emoji} [bold]NFS Mount:[/] {nfs_text}\n\n"
        fs_panel_content += "[bold underline]Local Disk Usage:[/]\n"
        fs_panel_content += f"[green]{disk_result.stdout}[/green]"

        console.print(Panel(
            fs_panel_content,
            title="💾 Filesystem Status",
            title_align="left",
            border_style="yellow"
        ))

    console.print("[bold green]✅ All checks complete.[/bold green]")


@service_cli.command(name="status", help="Get the status of a specific service.")
def service_status(
    service: Annotated[str, typer.Argument(
        help="The short name of the service (e.g., 'weppcloud').",
        autocompletion=lambda: SERVICE_ORDER
    )]
):
    """Show detailed systemctl status for a single service."""
    if service not in SERVICE_CONFIG:
        console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
        raise typer.Exit(code=1)
    
    systemd_name = SERVICE_CONFIG[service]['systemd']
    console.print(f"[bold]Querying status for [cyan]{systemd_name}[/cyan]...[/]")
    
    result = run_command(["systemctl", "status", systemd_name, "--no-pager"])
    
    # Colorize the output based on status
    output_style = "green" if "Active: active (running)" in result.stdout else "yellow"
    console.print(Panel(
        f"[{output_style}]{result.stdout}[/{output_style}]",
        title=f"Status: {service}",
        border_style=output_style
    ))


@service_cli.command(name="log", help="Tail the logs for a specific service.")
def service_log(
    service: Annotated[str, typer.Argument(
        help="The short name of the service to log.",
        autocompletion=lambda: SERVICE_ORDER
    )]
):
    """Follow the journalctl logs for a single service."""
    if service not in SERVICE_CONFIG:
        console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
        raise typer.Exit(code=1)

    systemd_name = SERVICE_CONFIG[service]['systemd']
    console.print(f"[bold]Tailing logs for [cyan]{systemd_name}[/cyan]. Press Ctrl+C to exit.[/]")
    try:
        # Use Popen to stream the output directly to the console
        process = subprocess.Popen(
            ["sudo", "journalctl", "-u", systemd_name, "-f", "-n", "50"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in iter(process.stdout.readline, ''):
            # Simple syntax highlighting for log levels
            if "error" in line.lower():
                console.print(f"[red]{line.strip()}[/red]")
            elif "warning" in line.lower():
                console.print(f"[yellow]{line.strip()}[/yellow]")
            else:
                print(line.strip())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Log tailing stopped.[/bold yellow]")
    finally:
        if process and process.poll() is None:
            process.terminate()


# A helper function to create start/stop/restart commands to avoid repetition
def create_service_action_command(action: str):
    """Factory function to generate service action commands."""
    @service_cli.command(name=action, help=f"{action.capitalize()} a specific service.")
    def service_action(
        service: Annotated[str, typer.Argument(
            help=f"The short name of the service to {action}.",
            autocompletion=lambda: SERVICE_ORDER
        )]
    ):
        if service not in SERVICE_CONFIG:
            console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
            raise typer.Exit(code=1)
        
        systemd_name = SERVICE_CONFIG[service]['systemd']
        spinner = Spinner("dots", text=f"[bold yellow]{action.capitalize()}ing {systemd_name}...[/]")
        with Live(spinner, console=console, transient=True, refresh_per_second=10):
            result = run_command(["systemctl", action, systemd_name])
            time.sleep(1) # Give systemd a moment

        if result.returncode == 0:
            console.print(f"[bold green]✅ Service '{systemd_name}' was {action}ed successfully.[/bold green]")
            # For restarts and starts, show the new status
            if action in ["restart", "start"]:
                 status_result = run_command(["systemctl", "status", systemd_name, "--no-pager"])
                 console.print(Panel(f"[green]{status_result.stdout}[/green]", padding=(1, 2)))
        else:
            console.print(f"[bold red]🔥 Error {action}ing service '{systemd_name}'.[/bold red]")
            console.print(Panel(f"[red]{result.stderr}[/red]", title="Error Details", border_style="red"))

    return service_action

# Create the start, stop, and restart commands
service_start = create_service_action_command("start")
service_stop = create_service_action_command("stop")
service_restart = create_service_action_command("restart")


if __name__ == "__main__":
    # Check for sudo access early, as most commands need it
    if os.geteuid() == 0:
        console.print("[yellow]Warning: Running as root. For `wctl`, it's better to run as a standard user with sudo privileges.[/yellow]")
    
        
    cli()
