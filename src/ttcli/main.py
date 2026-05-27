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


def _resolve_project(project: str) -> str:
    """Resolve a project name or ID to a project ID.

    If the input matches a project ID directly, use it as-is.
    Otherwise, search projects by name (case-insensitive, substring match).
    If exactly one match is found, use its ID.
    """
    with _get_client() as client:
        projects = client.list_projects()

    # Direct ID match
    for p in projects:
        if p.id == project:
            return project

    # Exact name match (case-insensitive)
    exact = [p for p in projects if p.name.lower() == project.lower()]
    if len(exact) == 1:
        return exact[0].id

    # Substring name match (case-insensitive)
    fuzzy = [p for p in projects if project.lower() in p.name.lower()]
    if len(fuzzy) == 1:
        return fuzzy[0].id
    elif len(fuzzy) > 1:
        console.print(f"[red]Error:[/red] Multiple projects match '{project}':")
        for m in fuzzy:
            console.print(f"  - {m.name} ({m.id})")
        console.print("Use the project ID instead.")
        raise typer.Exit(1)
    else:
        console.print(f"[red]Error:[/red] No project found matching '{project}'.")
        console.print("Run 'ttcli project list' to see all projects.")
        raise typer.Exit(1)


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
    project: str = typer.Option(
        ..., "--project", "-p",
        help="Project name or ID (name supports substring match)",
    ),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List tasks in a project."""
    from ttcli.models import Task

    project_id = _resolve_project(project)
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
        table.add_column("Title")
        table.add_column("Priority", justify="center")
        table.add_column("Status")
        for t in tasks:
            status_str = {0: "todo", 1: "doing", 2: "done"}.get(t.status, str(t.status))
            table.add_row(t.title, str(t.priority), status_str)
        console.print(table)


@task_app.command()
def get(
    task_id: str = typer.Argument(..., help="Task ID"),
    project: str = typer.Option(
        ..., "--project", "-p",
        help="Project name or ID (name supports substring match)",
    ),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get a single task by ID."""
    project_id = _resolve_project(project)
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
    project: str = typer.Option(
        ..., "--project", "-p",
        help="Project name or ID (name supports substring match)",
    ),
    content: str = typer.Option(None, "--content", "-c", help="Task content"),
    due_date: str = typer.Option(None, "--due-date", "-d", help="Due date (ISO 8601)"),
    priority: int = typer.Option(0, "--priority", help="Priority (0=none, 1=low, 3=medium, 5=high)"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new task."""
    from ttcli.models import Task as TaskModel

    project_id = _resolve_project(project)
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
    project: str = typer.Option(
        ..., "--project", "-p",
        help="Project name or ID (name supports substring match)",
    ),
    title: str = typer.Option(None, "--title", "-t", help="New title"),
    content: str = typer.Option(None, "--content", "-c", help="New content"),
    due_date: str = typer.Option(None, "--due-date", "-d", help="New due date"),
    priority: int = typer.Option(None, "--priority", help="New priority"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Update a task. Omitted fields are left unchanged."""
    project_id = _resolve_project(project)
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
    project: str = typer.Option(
        ..., "--project", "-p",
        help="Project name or ID (name supports substring match)",
    ),
) -> None:
    """Delete a task."""
    project_id = _resolve_project(project)
    with _get_client() as client:
        client.delete_task(project_id, task_id)
    console.print(f"[green]✅ Task deleted:[/green] {task_id}")


@task_app.command()
def complete(
    task_id: str = typer.Argument(..., help="Task ID"),
    project: str = typer.Option(
        ..., "--project", "-p",
        help="Project name or ID (name supports substring match)",
    ),
) -> None:
    """Mark a task as completed."""
    project_id = _resolve_project(project)
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
        table.add_column("Title")
        table.add_column("Priority", justify="center")
        table.add_column("Status")
        for t in tasks:
            status_str = {0: "todo", 1: "doing", 2: "done"}.get(t.status, str(t.status))
            table.add_row(t.title, str(t.priority), status_str)
        console.print(table)


# ------------------------------------------------------------------
# Project commands
# ------------------------------------------------------------------


@project_app.callback()
def project_callback() -> None:
    pass


@project_app.command()
def list(
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all projects."""
    with _get_client() as client:
        projects = client.list_projects()

    if json:
        console.print(json_lib.dumps(
            [p.model_dump(exclude_none=True) for p in projects], indent=2
        ))
    else:
        if not projects:
            console.print("[yellow]No projects found.[/yellow]")
            return
        table = Table(title="Projects")
        table.add_column("Name")
        table.add_column("Kind")
        for p in projects:
            table.add_row(p.name, p.kind or "")
        console.print(table)


@project_app.command()
def get(
    project_id: str = typer.Argument(..., help="Project ID"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get a single project by ID."""
    with _get_client() as client:
        project = client.get_project(project_id)

    if json:
        console.print(json_lib.dumps(project.model_dump(exclude_none=True), indent=2))
    else:
        info = f"[bold]Name:[/bold] {project.name}\n"
        if project.color:
            info += f"[bold]Color:[/bold] {project.color}\n"
        if project.kind:
            info += f"[bold]Kind:[/bold] {project.kind}\n"
        if project.viewMode:
            info += f"[bold]View:[/bold] {project.viewMode}\n"
        if project.closed is not None:
            info += f"[bold]Closed:[/bold] {project.closed}\n"
        console.print(Panel(info, title=f"Project {project.id}"))


@project_app.command()
def create(
    name: str = typer.Argument(..., help="Project name"),
    color: str = typer.Option(None, "--color", help="Project color (hex)"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new project."""
    from ttcli.models import Project as ProjectModel

    project = ProjectModel(name=name, color=color)
    with _get_client() as client:
        created = client.create_project(project)

    if json:
        console.print(json_lib.dumps(created.model_dump(exclude_none=True), indent=2))
    else:
        console.print(f"[green]✅ Project created:[/green] '{created.name}' (id={created.id})")


@project_app.command()
def update(
    project_id: str = typer.Argument(..., help="Project ID"),
    name: str = typer.Option(None, "--name", "-n", help="New name"),
    color: str = typer.Option(None, "--color", help="New color (hex)"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Update a project."""
    with _get_client() as client:
        current = client.get_project(project_id)
        if name is not None:
            current.name = name
        if color is not None:
            current.color = color
        updated = client.update_project(project_id, current)

    if json:
        console.print(json_lib.dumps(updated.model_dump(exclude_none=True), indent=2))
    else:
        console.print(f"[green]✅ Project updated:[/green] '{updated.name}'")


@project_app.command()
def delete(
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """Delete a project."""
    with _get_client() as client:
        client.delete_project(project_id)
    console.print(f"[green]✅ Project deleted:[/green] {project_id}")


@project_app.command()
def data(
    project_id: str = typer.Argument(..., help="Project ID"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get full project data with tasks and columns."""
    with _get_client() as client:
        result = client.get_project_data(project_id)

    if json:
        console.print(json_lib.dumps(result, indent=2, default=str))
    else:
        proj_info = result.get("project", result)
        console.print(f"[bold]Project:[/bold] {proj_info.get('name', project_id)}")
        console.print(f"[bold]ID:[/bold] {proj_info.get('id')}\n")

        tasks = result.get("tasks", [])
        if tasks:
            table = Table(title="Tasks")
            table.add_column("Title")
            table.add_column("Priority", justify="center")
            table.add_column("Status")
            for t in tasks:
                status_str = {0: "todo", 1: "doing", 2: "done"}.get(t.get("status", 0), str(t.get("status", 0)))
                table.add_row(
                    t.get("title", ""),
                    str(t.get("priority", 0)),
                    status_str,
                )
            console.print(table)

        columns = result.get("columns", [])
        if columns:
            col_table = Table(title="Columns")
            col_table.add_column("Name")
            col_table.add_column("Sort Order", justify="center")
            for c in columns:
                col_table.add_row(
                    c.get("name", ""),
                    str(c.get("sortOrder", 0)),
                )
            console.print(col_table)


if __name__ == "__main__":
    app()
