import json as json_lib
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="ttcli",
    help="Minimal TickTick CLI",
)

auth_app = typer.Typer(name="auth", help="Authentication commands")
task_app = typer.Typer(name="task", help="Task commands")
project_app = typer.Typer(name="project", help="Project commands")

app.add_typer(auth_app)
app.add_typer(task_app)
app.add_typer(project_app)

console = Console()


def _auth_dir() -> Path:
    env_dir = os.environ.get("TTCLI_AUTH_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".ttcli"


def _get_client():
    """Create a TickTickClient from stored tokens."""
    from ttcli.client import api_client, ClientError

    try:
        return api_client(storage_dir=_auth_dir())
    except ClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ------------------------------------------------------------------
# Auth commands
# ------------------------------------------------------------------


@auth_app.callback()
def auth_callback() -> None:
    pass


@auth_app.command()
def setup(
    client_id: str = typer.Option(
        ..., "--client-id", "-i", prompt=True, help="TickTick OAuth client ID"
    ),
    client_secret: str = typer.Option(
        ..., "--client-secret", "-s", prompt=True, hide_input=True,
        help="TickTick OAuth client secret",
    ),
) -> None:
    """Authenticate with TickTick via OAuth2 authorization code flow."""
    from ttcli.auth import authenticate_local_server

    authenticate_local_server(client_id, client_secret, storage_dir=_auth_dir())
    console.print("[green]✅ Authentication successful. Tokens saved.[/green]")


@auth_app.command()
def status(
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Check authentication status."""
    from ttcli.auth import is_authenticated, load_tokens

    authed = is_authenticated(storage_dir=_auth_dir())
    if json:
        data = {"authenticated": authed}
        if authed:
            token = load_tokens(storage_dir=_auth_dir())
            data["expires_at"] = (
                token.obtained_at.isoformat() if token and token.obtained_at else None
            )
        console.print(json_lib.dumps(data))
    else:
        if authed:
            console.print("[green]✅ Authenticated[/green]")
        else:
            console.print("[yellow]❌ Not authenticated.[/yellow] Run 'ttcli auth setup' first.")


@auth_app.command()
def refresh(
    client_id: str = typer.Option(
        ..., "--client-id", "-i", prompt=True, help="TickTick OAuth client ID"
    ),
    client_secret: str = typer.Option(
        ..., "--client-secret", "-s", prompt=True, hide_input=True,
        help="TickTick OAuth client secret",
    ),
) -> None:
    """Refresh the access token."""
    from ttcli.auth import refresh_access_token, load_tokens, AuthError

    token = load_tokens(storage_dir=_auth_dir())
    if token is None:
        console.print("[red]Error:[/red] No tokens found. Run 'ttcli auth setup' first.")
        raise typer.Exit(1)

    try:
        refresh_access_token(
            token.refresh_token, client_id, client_secret,
            storage_dir=_auth_dir(),
        )
        console.print("[green]✅ Token refreshed.[/green]")
    except AuthError as e:
        console.print(f"[red]Error:[/red] Failed to refresh token: {e}")
        raise typer.Exit(1)


# ------------------------------------------------------------------
# Task commands
# ------------------------------------------------------------------


@task_app.callback()
def task_callback() -> None:
    pass


@task_app.command()
def list(
    project_id: str = typer.Option(..., "--project-id", "-p", help="Project ID"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List tasks in a project."""
    from ttcli.models import Task

    with _get_client() as client:
        tasks = client.list_tasks(project_id)

    if json:
        console.print(json_lib.dumps(
            [t.model_dump(exclude_none=True) for t in tasks], indent=2
        ))
    else:
        if not tasks:
            console.print("[yellow]No tasks found.[/yellow]")
            return
        table = Table(title=f"Tasks")
        table.add_column("ID", style="dim")
        table.add_column("Title")
        table.add_column("Priority", justify="center")
        table.add_column("Status")
        for t in tasks:
            status_str = {0: "todo", 1: "doing", 2: "done"}.get(t.status, str(t.status))
            table.add_row(t.id or "", t.title, str(t.priority), status_str)
        console.print(table)


@task_app.command()
def get(
    task_id: str = typer.Argument(..., help="Task ID"),
    project_id: str = typer.Option(..., "--project-id", "-p", help="Project ID"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get a single task by ID."""
    with _get_client() as client:
        task = client.get_task(project_id, task_id)

    if json:
        console.print(json_lib.dumps(task.model_dump(exclude_none=True), indent=2))
    else:
        info = f"[bold]Title:[/bold] {task.title}\n"
        if task.content:
            info += f"[bold]Content:[/bold] {task.content}\n"
        info += f"[bold]Priority:[/bold] {task.priority}\n"
        info += f"[bold]Status:[/bold] {task.status}\n"
        if task.dueDate:
            info += f"[bold]Due:[/bold] {task.dueDate}\n"
        if task.tags:
            info += f"[bold]Tags:[/bold] {', '.join(task.tags)}\n"
        console.print(Panel(info, title=f"Task {task.id}"))


@task_app.command()
def create(
    title: str = typer.Argument(..., help="Task title"),
    project_id: str = typer.Option(..., "--project-id", "-p", help="Project ID"),
    content: str = typer.Option(None, "--content", "-c", help="Task content"),
    due_date: str = typer.Option(None, "--due-date", "-d", help="Due date (ISO 8601)"),
    priority: int = typer.Option(0, "--priority", help="Priority (0=none, 1=low, 3=medium, 5=high)"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new task."""
    from ttcli.models import Task as TaskModel

    task = TaskModel(
        title=title,
        projectId=project_id,
        content=content,
        dueDate=due_date,
        priority=priority,
    )
    with _get_client() as client:
        created = client.create_task(task)

    if json:
        console.print(json_lib.dumps(created.model_dump(exclude_none=True), indent=2))
    else:
        console.print(f"[green]✅ Task created:[/green] '{created.title}' (id={created.id})")


@task_app.command()
def update(
    task_id: str = typer.Argument(..., help="Task ID"),
    project_id: str = typer.Option(..., "--project-id", "-p", help="Project ID"),
    title: str = typer.Option(None, "--title", "-t", help="New title"),
    content: str = typer.Option(None, "--content", "-c", help="New content"),
    due_date: str = typer.Option(None, "--due-date", "-d", help="New due date"),
    priority: int = typer.Option(None, "--priority", help="New priority"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Update a task. Omitted fields are left unchanged."""
    # Fetch current task first
    with _get_client() as client:
        current = client.get_task(project_id, task_id)

    # Apply changes
    if title is not None:
        current.title = title
    if content is not None:
        current.content = content
    if due_date is not None:
        current.dueDate = due_date
    if priority is not None:
        current.priority = priority

    with _get_client() as client:
        updated = client.update_task(project_id, task_id, current)

    if json:
        console.print(json_lib.dumps(updated.model_dump(exclude_none=True), indent=2))
    else:
        console.print(f"[green]✅ Task updated:[/green] '{updated.title}'")


@task_app.command()
def delete(
    task_id: str = typer.Argument(..., help="Task ID"),
    project_id: str = typer.Option(..., "--project-id", "-p", help="Project ID"),
) -> None:
    """Delete a task."""
    with _get_client() as client:
        client.delete_task(project_id, task_id)
    console.print(f"[green]✅ Task deleted:[/green] {task_id}")


@task_app.command()
def complete(
    task_id: str = typer.Argument(..., help="Task ID"),
    project_id: str = typer.Option(..., "--project-id", "-p", help="Project ID"),
) -> None:
    """Mark a task as completed."""
    with _get_client() as client:
        client.complete_task(project_id, task_id)
    console.print(f"[green]✅ Task completed:[/green] {task_id}")


@task_app.command()
def filter(
    project_ids: str = typer.Option(None, "--project-ids", help="Comma-separated project IDs"),
    status: str = typer.Option(None, "--status", help="Status code (0=todo, 2=done)"),
    priority: str = typer.Option(None, "--priority", help="Comma-separated priority values"),
    start_date: str = typer.Option(None, "--start-date", help="Start date filter"),
    end_date: str = typer.Option(None, "--end-date", help="End date filter"),
    tag: str = typer.Option(None, "--tag", help="Comma-separated tags"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Filter tasks by criteria."""
    kwargs = {}
    if project_ids:
        kwargs["project_ids"] = [p.strip() for p in project_ids.split(",")]
    if status:
        kwargs["status"] = [int(s.strip()) for s in status.split(",")]
    if priority:
        kwargs["priority"] = [int(p.strip()) for p in priority.split(",")]
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    if tag:
        kwargs["tag"] = [t.strip() for t in tag.split(",")]

    with _get_client() as client:
        tasks = client.filter_tasks(**kwargs)

    if json:
        console.print(json_lib.dumps(
            [t.model_dump(exclude_none=True) for t in tasks], indent=2
        ))
    else:
        if not tasks:
            console.print("[yellow]No tasks found matching criteria.[/yellow]")
            return
        table = Table(title="Filtered Tasks")
        table.add_column("ID", style="dim")
        table.add_column("Title")
        table.add_column("Priority", justify="center")
        table.add_column("Status")
        for t in tasks:
            status_str = {0: "todo", 1: "doing", 2: "done"}.get(t.status, str(t.status))
            table.add_row(t.id or "", t.title, str(t.priority), status_str)
        console.print(table)


# ------------------------------------------------------------------
# Project commands (placeholder)
# ------------------------------------------------------------------


@project_app.callback()
def project_callback() -> None:
    pass


@project_app.command()
def list() -> None:
    """List projects (not yet implemented)."""
    console.print("Project commands coming soon.")


if __name__ == "__main__":
    app()
