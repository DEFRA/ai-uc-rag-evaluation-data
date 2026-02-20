"""Command-line interface for the Defra Data API (knowledge management)."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

from app.client.client import DefraDataClient
from app.client.models import (
    CreateKnowledgeGroupRequest,
    KnowledgeSourceInput,
    SourceType,
)

app = typer.Typer(
    help="Defra Data API CLI — knowledge groups, snapshots, and vector search."
)

groups_app = typer.Typer(help="Knowledge group commands.")
app.add_typer(groups_app, name="groups")

snapshots_app = typer.Typer(help="Snapshot commands.")
app.add_typer(snapshots_app, name="snapshots")

console = Console()


def _to_serializable(obj: Any) -> Any:
    """Convert dataclass/enum to JSON-serializable dict."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_serializable(v) for k, v in asdict(obj).items()}
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    return obj


class CliContext:
    def __init__(
        self,
        base_url: str = "http://data.localhost",
        timeout: float = 30.0,
        json_output: bool = False,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.json_output = json_output

    def client(self) -> DefraDataClient:
        return DefraDataClient(base_url=self.base_url, timeout=self.timeout)


@app.callback()
def cli_callback(
    ctx: typer.Context,
    base_url: str = typer.Option(
        "http://data.localhost",
        "--base-url",
        "-u",
        envvar="DEFRA_DATA_URL",
        help="API base URL",
    ),
    timeout: float = typer.Option(
        30.0, "--timeout", "-t", help="Request timeout in seconds"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
) -> None:
    ctx.obj = CliContext(base_url=base_url, timeout=timeout, json_output=json_output)


# --- Groups ---


@groups_app.command("list")
def groups_list(ctx: typer.Context) -> None:
    """List all knowledge groups."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        groups = client.list_groups()

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(groups), indent=2))
        return

    table = Table(title="Knowledge Groups")
    table.add_column("group_id", style="cyan")
    table.add_column("title", style="white")
    table.add_column("owner", style="green")
    for g in groups:
        table.add_row(g.group_id, g.title, g.owner)
    console.print(table)


@groups_app.command("get")
def groups_get(ctx: typer.Context, group_id: str) -> None:
    """Get a knowledge group by ID."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        group = client.get_group(group_id)

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(group), indent=2))
        return

    sources_str = ", ".join(
        f"{s.source_id}: {s.name} ({s.type.value})" for s in group.sources.values()
    )
    console.print(f"[bold]{group.title}[/bold] ({group.group_id})")
    console.print(f"  Owner: {group.owner}")
    console.print(f"  Description: {group.description}")
    console.print(f"  Sources: {sources_str or 'none'}")


@groups_app.command("create")
def groups_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Group name"),
    description: str = typer.Option(
        ..., "--description", "-d", help="Group description"
    ),
    owner: str = typer.Option(..., "--owner", "-o", help="Owner identifier"),
    source: list[str] = typer.Option(
        [],
        "--source",
        "-s",
        help="Source as name:type:location (repeat for multiple). Type: BLOB or PRECHUNKED_BLOB",
    ),
) -> None:
    """Create a new knowledge group."""
    sources: list[KnowledgeSourceInput] = []
    for s in source:
        parts = s.split(":", 2)
        if len(parts) != 3:
            msg = "--source must be name:type:location"
            raise typer.BadParameter(msg)
        name_part, type_part, location = parts
        try:
            src_type = SourceType(type_part.strip())
        except ValueError:
            msg = f"type must be BLOB or PRECHUNKED_BLOB, got {type_part}"
            raise typer.BadParameter(msg) from None
        sources.append(
            KnowledgeSourceInput(
                name=name_part.strip(), type=src_type, location=location
            )
        )

    cfg: CliContext = ctx.obj
    req = CreateKnowledgeGroupRequest(
        name=name, description=description, owner=owner, sources=sources
    )
    with cfg.client() as client:
        group = client.create_group(req)

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(group), indent=2))
        return

    console.print(f"[green]Created group[/green] {group.group_id}: {group.title}")


@groups_app.command("add-source")
def groups_add_source(
    ctx: typer.Context,
    group_id: str = typer.Argument(..., help="Group ID"),
    name: str = typer.Option(..., "--name", "-n", help="Source name"),
    type_str: str = typer.Option(..., "--type", "-t", help="BLOB or PRECHUNKED_BLOB"),
    location: str = typer.Option(
        ..., "--location", "-l", help="Source location (e.g. s3://...)"
    ),
) -> None:
    """Add a source to a knowledge group."""
    try:
        src_type = SourceType(type_str)
    except ValueError:
        msg = f"type must be BLOB or PRECHUNKED_BLOB, got {type_str}"
        raise typer.BadParameter(msg) from None
    cfg: CliContext = ctx.obj
    source = KnowledgeSourceInput(name=name, type=src_type, location=location)
    with cfg.client() as client:
        group = client.add_source(group_id, source)

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(group), indent=2))
        return

    console.print(f"[green]Added source[/green] {name} to group {group_id}")


@groups_app.command("ingest")
def groups_ingest(
    ctx: typer.Context, group_id: str = typer.Argument(..., help="Group ID")
) -> None:
    """Trigger ingestion for a knowledge group."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        result = client.ingest_group(group_id)

    if cfg.json_output:
        console.print(json.dumps(result, indent=2))
        return

    console.print(f"[green]Ingestion triggered[/green] for {group_id}")
    console.print(json.dumps(result, indent=2))


@groups_app.command("snapshots")
def groups_snapshots(
    ctx: typer.Context,
    group_id: str = typer.Argument(..., help="Group ID"),
) -> None:
    """List snapshots for a knowledge group."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        snapshots = client.list_group_snapshots(group_id)

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(snapshots), indent=2))
        return

    table = Table(title=f"Snapshots for {group_id}")
    table.add_column("snapshot_id", style="cyan")
    table.add_column("version", style="white")
    table.add_column("created_at", style="green")
    for s in snapshots:
        table.add_row(s.snapshot_id, str(s.version), s.created_at)
    console.print(table)


# --- Snapshots ---


@snapshots_app.command("get")
def snapshots_get(
    ctx: typer.Context,
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
) -> None:
    """Get a snapshot by ID."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        snapshot = client.get_snapshot(snapshot_id)

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(snapshot), indent=2))
        return

    console.print(f"[bold]Snapshot[/bold] {snapshot.snapshot_id}")
    console.print(f"  Group: {snapshot.group_id}")
    console.print(f"  Version: {snapshot.version}")
    console.print(f"  Created: {snapshot.created_at}")


@snapshots_app.command("activate")
def snapshots_activate(
    ctx: typer.Context,
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
) -> None:
    """Activate a snapshot for its knowledge group."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        result = client.activate_snapshot(snapshot_id)

    if cfg.json_output:
        console.print(json.dumps(result, indent=2))
        return

    console.print(f"[green]Activated[/green] snapshot {snapshot_id}")
    console.print(json.dumps(result, indent=2))


# --- Query ---


@app.command()
def query(
    ctx: typer.Context,
    group_id: str = typer.Argument(..., help="Knowledge group ID"),
    query_text: str = typer.Argument(..., help="Search query"),
    max_results: int = typer.Option(
        5, "--max-results", "-n", help="Max results to return"
    ),
) -> None:
    """Query a group's active snapshot (vector search)."""
    cfg: CliContext = ctx.obj
    with cfg.client() as client:
        result = client.query(group_id, query_text, max_results=max_results)

    if cfg.json_output:
        console.print(json.dumps(_to_serializable(result), indent=2))
        return

    table = Table(title="Query Results")
    table.add_column("name", style="cyan")
    table.add_column("score", style="green")
    table.add_column("content", style="white", max_width=60, overflow="fold")
    for r in result.results:
        table.add_row(
            r.name,
            f"{r.similarity_score:.3f}",
            r.content[:200] + "..." if len(r.content) > 200 else r.content,
        )
    console.print(table)


def main() -> None:
    try:
        app()
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
