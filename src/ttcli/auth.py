import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

AUTH_DIR_DEFAULT = Path.home() / ".ttcli"
TOKEN_FILE = "auth.json"
DEVICE_AUTH_URL = "https://api.ticktick.com/oauth/token"


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


def _post_json(client: httpx.Client, url: str, data: dict) -> dict:
    """POST form-encoded data (OAuth2 uses form-encoding, not JSON body)."""
    resp = client.post(url, data=data)
    if resp.status_code >= 400:
        body = resp.json() if resp.text else {}
        error = body.get("error", "unknown_error")
        raise AuthError(error)
    return resp.json()


def authenticate_device(
    client_id: str,
    client_secret: str,
    storage_dir: Path | None = None,
    http_client: httpx.Client | None = None,
) -> TokenData:
    """Run OAuth2 device flow.

    1. Request device code
    2. Print user_code + verification_uri for the user
    3. Poll token endpoint until user completes
    4. Save and return TokenData
    """
    close_client = http_client is None
    client = http_client or httpx.Client()

    try:
        # Step 1: Request device code
        device_resp = _post_json(
            client,
            DEVICE_AUTH_URL,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "device_code",
            },
        )

        device_code = device_resp["device_code"]
        user_code = device_resp["user_code"]
        verification_uri = device_resp.get(
            "verification_uri", "https://ticktick.com/activate"
        )
        interval = device_resp.get("interval", 5)

        print(f"\nOpen this URL in your browser: {verification_uri}")
        print(f"Enter code: {user_code}\n")

        # Step 2: Poll for token
        while True:
            time.sleep(interval)
            try:
                token_resp = _post_json(
                    client,
                    DEVICE_AUTH_URL,
                    {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "device_token",
                        "device_code": device_code,
                    },
                )
                break
            except AuthError as e:
                error = str(e)
                if error == "authorization_pending":
                    continue
                raise

        token = TokenData(
            access_token=token_resp["access_token"],
            refresh_token=token_resp["refresh_token"],
            expires_in=token_resp.get("expires_in", 3600),
            token_type=token_resp.get("token_type", "Bearer"),
            scope=token_resp.get("scope"),
        )

        save_tokens(token, storage_dir)
        return token

    finally:
        if close_client:
            client.close()


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
        token_resp = _post_json(
            client,
            DEVICE_AUTH_URL,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

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
