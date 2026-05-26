import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
from pydantic import BaseModel

AUTH_DIR_DEFAULT = Path.home() / ".ttcli"
TOKEN_FILE = "auth.json"
TOKEN_URL = "https://api.ticktick.com/oauth/token"
AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"


class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    scope: str | None = None
    obtained_at: datetime | None = None

    def model_post_init(self, __context) -> None:
        if self.obtained_at is None:
            self.obtained_at = datetime.now(timezone.utc)

    @property
    def is_expired(self) -> bool:
        if self.obtained_at is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.obtained_at).total_seconds()
        return elapsed >= self.expires_in


class AuthError(Exception):
    pass


def _auth_path(storage_dir: Path | None = None) -> Path:
    base = storage_dir or AUTH_DIR_DEFAULT
    return base / TOKEN_FILE


def save_tokens(token: TokenData, storage_dir: Path | None = None) -> None:
    path = _auth_path(storage_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.model_dump_json())


def load_tokens(storage_dir: Path | None = None) -> TokenData | None:
    path = _auth_path(storage_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return TokenData(**data)
    except (json.JSONDecodeError, ValueError):
        return None


def is_authenticated(storage_dir: Path | None = None) -> bool:
    token = load_tokens(storage_dir)
    if token is None:
        return False
    return not token.is_expired


def _exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> TokenData:
    """Exchange an authorization code for an access token."""
    resp = httpx.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "scope": "tasks:write tasks:read",
        },
    )
    if resp.status_code >= 400:
        body = resp.json() if resp.text else {}
        error = body.get("error", resp.text)
        raise AuthError(f"Token exchange failed: {error}")
    body = resp.json()
    return TokenData(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token", ""),
        expires_in=body.get("expires_in", 3600),
        token_type=body.get("token_type", "Bearer"),
        scope=body.get("scope"),
    )


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler that captures the OAuth callback."""

    code: str | None = None
    received = threading.Event()

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        code_list = params.get("code")

        if code_list:
            _CallbackHandler.code = code_list[0]
            _CallbackHandler.received.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization successful!</h1>"
                b"<p>You can close this tab and return to the terminal.</p></body></html>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing 'code' parameter in callback URL.")

    def log_message(self, format, *args):
        pass  # Suppress HTTP server logs


def authenticate_local_server(
    client_id: str,
    client_secret: str,
    storage_dir: Path | None = None,
    port: int = 6600,
) -> TokenData:
    """Authenticate via OAuth2 authorization code flow with a local web server.

    Starts a temporary HTTP server on localhost, opens the browser to the
    TickTick authorization page, and catches the redirect automatically.

    The port must match the registered OAuth redirect URI in the TickTick
    developer portal (default: 6600).
    """
    redirect_uri = f"http://localhost:{port}/callback"

    auth_url = (
        f"{AUTHORIZE_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=tasks:write%20tasks:read"
        f"&state=ttcli"
    )

    # Reset shared state
    _CallbackHandler.code = None
    _CallbackHandler.received.clear()

    server = HTTPServer(("localhost", port), _CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"\n  Opening browser for TickTick authorization...\n")
    print(f"  If the browser doesn't open, visit this URL:")
    print(f"  {auth_url}\n")

    import webbrowser
    webbrowser.open(auth_url)

    print(f"  Waiting for authorization...")
    _CallbackHandler.received.wait(timeout=300)
    server.shutdown()

    if _CallbackHandler.code is None:
        raise AuthError("Authorization timed out or was cancelled.")

    code = _CallbackHandler.code
    token = _exchange_code(code, client_id, client_secret, redirect_uri)
    save_tokens(token, storage_dir)
    print(f"  ✅ Authorized successfully.\n")
    return token


def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
    storage_dir: Path | None = None,
    http_client: httpx.Client | None = None,
) -> TokenData:
    """Refresh an expired access token and save the new tokens."""
    close_client = http_client is None
    client = http_client or httpx.Client()

    try:
        resp = client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        if resp.status_code >= 400:
            body = resp.json() if resp.text else {}
            error = body.get("error", resp.text)
            raise AuthError(f"Token refresh failed: {error}")

        token_resp = resp.json()
        token = TokenData(
            access_token=token_resp["access_token"],
            refresh_token=token_resp.get("refresh_token", refresh_token),
            expires_in=token_resp.get("expires_in", 3600),
            token_type=token_resp.get("token_type", "Bearer"),
            scope=token_resp.get("scope"),
        )

        save_tokens(token, storage_dir)
        return token

    finally:
        if close_client:
            client.close()
