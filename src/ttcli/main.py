import os
from pathlib import Path

import typer

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


def _auth_dir() -> Path:
    """Get auth storage directory from env or default."""
    env_dir = os.environ.get("TTCLI_AUTH_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".ttcli"


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
    """Authenticate with TickTick via OAuth2 authorization code flow.

    Opens a browser window for you to authorize the application.
    Tokens are saved to ~/.ttcli/auth.json for future use.
    """
    from ttcli.auth import authenticate_local_server

    authenticate_local_server(client_id, client_secret, storage_dir=_auth_dir())
    typer.echo("✅ Authentication successful. Tokens saved.")


@auth_app.command()
def status(
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Check authentication status."""
    from ttcli.auth import is_authenticated, load_tokens

    authed = is_authenticated(storage_dir=_auth_dir())
    if json:
        import json as json_lib
        data = {"authenticated": authed}
        if authed:
            token = load_tokens(storage_dir=_auth_dir())
            data["expires_at"] = (
                token.obtained_at.isoformat() if token and token.obtained_at else None
            )
        typer.echo(json_lib.dumps(data))
    else:
        if authed:
            typer.echo("✅ Authenticated")
        else:
            typer.echo("❌ Not authenticated. Run 'ttcli auth setup' first.")


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
        typer.echo("❌ No tokens found. Run 'ttcli auth setup' first.", err=True)
        raise typer.Exit(1)

    try:
        refresh_access_token(
            token.refresh_token, client_id, client_secret,
            storage_dir=_auth_dir(),
        )
        typer.echo("✅ Token refreshed.")
    except AuthError as e:
        typer.echo(f"❌ Failed to refresh token: {e}", err=True)
        raise typer.Exit(1)


# ------------------------------------------------------------------
# Task commands (placeholder)
# ------------------------------------------------------------------

@task_app.callback()
def task_callback() -> None:
    pass


@task_app.command()
def list() -> None:
    """List tasks (not yet implemented)."""
    typer.echo("Task commands coming soon.")


# ------------------------------------------------------------------
# Project commands (placeholder)
# ------------------------------------------------------------------

@project_app.callback()
def project_callback() -> None:
    pass


@project_app.command()
def list() -> None:
    """List projects (not yet implemented)."""
    typer.echo("Project commands coming soon.")


if __name__ == "__main__":
    app()
