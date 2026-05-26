import json
from pathlib import Path

import pytest
from httpx import Client, HTTPStatusError
from pydantic import ValidationError

from ttcli.auth import (
    TokenData,
    AuthError,
    load_tokens,
    save_tokens,
    authenticate_device,
    refresh_access_token,
    is_authenticated,
)


class TestTokenData:
    def test_create_with_required_fields(self):
        token = TokenData(access_token="abc", refresh_token="def", expires_in=3600)
        assert token.access_token == "abc"
        assert token.refresh_token == "def"
        assert token.expires_in == 3600
        assert token.token_type == "Bearer"
        assert token.obtained_at is not None

    def test_create_with_all_fields(self):
        token = TokenData(
            access_token="abc",
            refresh_token="def",
            expires_in=3600,
            token_type="Bearer",
            scope="tasks:read",
        )
        assert token.scope == "tasks:read"

    def test_access_token_is_required(self):
        with pytest.raises(ValidationError):
            TokenData(refresh_token="def", expires_in=3600)

    def test_refresh_token_is_required(self):
        with pytest.raises(ValidationError):
            TokenData(access_token="abc", expires_in=3600)

    def test_expires_in_is_required(self):
        with pytest.raises(ValidationError):
            TokenData(access_token="abc", refresh_token="def")


class TestTokenStorage:
    def test_save_and_load_tokens(self, tmp_path):
        token = TokenData(
            access_token="abc123",
            refresh_token="def456",
            expires_in=3600,
        )
        save_tokens(token, tmp_path)
        token_file = tmp_path / "auth.json"
        assert token_file.exists()
        loaded = load_tokens(tmp_path)
        assert loaded is not None
        assert loaded.access_token == "abc123"
        assert loaded.refresh_token == "def456"
        assert loaded.expires_in == 3600

    def test_load_tokens_returns_none_when_no_file(self, tmp_path):
        assert load_tokens(tmp_path) is None

    def test_load_tokens_returns_none_on_corrupt_file(self, tmp_path):
        token_file = tmp_path / "auth.json"
        token_file.write_text("not valid json{")
        assert load_tokens(tmp_path) is None

    def test_is_authenticated_with_valid_token(self, tmp_path):
        token = TokenData(
            access_token="abc",
            refresh_token="def",
            expires_in=3600,
        )
        save_tokens(token, tmp_path)
        assert is_authenticated(tmp_path) is True

    def test_is_authenticated_with_no_token(self, tmp_path):
        assert is_authenticated(tmp_path) is False


class TestAuthenticateDevice:
    def test_successful_device_auth(self, tmp_path, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            json={
                "device_code": "dev-123",
                "user_code": "ABC-DEF",
                "verification_uri": "https://ticktick.com/activate",
                "interval": 1,
            },
        )
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            json={
                "access_token": "at-123",
                "refresh_token": "rt-123",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

        result = authenticate_device("client-123", "secret-456", storage_dir=tmp_path)
        assert result.access_token == "at-123"
        assert result.refresh_token == "rt-123"
        assert is_authenticated(tmp_path) is True

    def test_auth_polls_until_complete(self, tmp_path, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            json={
                "device_code": "dev-123",
                "user_code": "ABC-DEF",
                "verification_uri": "https://ticktick.com/activate",
                "interval": 1,
            },
        )
        # First poll: authorization_pending
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            status_code=400,
            json={"error": "authorization_pending"},
        )
        # Second poll: success
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            json={
                "access_token": "at-456",
                "refresh_token": "rt-456",
                "expires_in": 7200,
            },
        )

        result = authenticate_device("client-123", "secret-456", storage_dir=tmp_path)
        assert result.access_token == "at-456"

    def test_raises_auth_error_on_invalid_client(self, tmp_path, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            status_code=400,
            json={"error": "invalid_client"},
        )
        with pytest.raises(AuthError, match="invalid_client"):
            authenticate_device("bad-client", "bad-secret", storage_dir=tmp_path)


class TestRefreshAccessToken:
    def test_successful_refresh(self, tmp_path, httpx_mock):
        token = TokenData(
            access_token="old-at",
            refresh_token="rt-123",
            expires_in=3600,
        )
        save_tokens(token, tmp_path)

        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            json={
                "access_token": "new-at",
                "refresh_token": "new-rt",
                "expires_in": 3600,
            },
        )

        result = refresh_access_token("rt-123", "client-123", "secret-456", storage_dir=tmp_path)
        assert result.access_token == "new-at"
        assert result.refresh_token == "new-rt"

        # Verify stored tokens are updated
        loaded = load_tokens(tmp_path)
        assert loaded is not None
        assert loaded.access_token == "new-at"
        assert loaded.refresh_token == "new-rt"

    def test_refresh_raises_on_failure(self, tmp_path, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            status_code=400,
            json={"error": "invalid_grant"},
        )
        with pytest.raises(AuthError, match="invalid_grant"):
            refresh_access_token("bad-rt", "client-123", "secret-456", storage_dir=tmp_path)
