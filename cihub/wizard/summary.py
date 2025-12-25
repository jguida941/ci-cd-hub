"""Rich summary output for wizard results."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table


def print_config_summary(console: Console, config: dict) -> None:
    """Print a high-level config summary."""
    console.print("[bold]Config Summary[/bold]")
    console.print_json(data=config)


def print_tool_table(console: Console, tools: dict) -> None:
    """Print a table of tool enablement."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Tool")
    table.add_column("Enabled")
    for tool, data in sorted(tools.items()):
        enabled = data.get("enabled", False)
        table.add_row(tool, "true" if enabled else "false")
    console.print(table)


def print_save_confirmation(console: Console, path: str) -> None:
    """Print a save confirmation message."""
    console.print(f"[bold green]Saved:[/bold green] {path}")
