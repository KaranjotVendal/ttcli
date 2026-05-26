from pathlib import Path

import pytest
from typer.testing import CliRunner

from ttcli.main import app

runner = CliRunner()


class TestAuthCli:
    def test_help_shows_auth_group(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "auth" in result.stdout
        assert "task" in result.stdout
        assert "project" in result.stdout

    def test_auth_help_shows_commands(self):
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.stdout
        assert "status" in result.stdout
        assert "refresh" in result.stdout

    def test_auth_status_not_authenticated(self, tmp_path):
        result = runner.invoke(
            app, ["auth", "status"],
            env={"TTCLI_AUTH_DIR": str(tmp_path)},
        )
        assert result.exit_code == 0
        assert "not authenticated" in result.stdout.lower()

    def test_auth_status_authenticated(self, tmp_path):
        from ttcli.auth import save_tokens, TokenData

        token = TokenData(access_token="a", refresh_token="b", expires_in=3600)
        save_tokens(token, tmp_path)

        result = runner.invoke(
            app, ["auth", "status"],
            env={"TTCLI_AUTH_DIR": str(tmp_path)},
        )
        assert result.exit_code == 0
        assert "authenticated" in result.stdout.lower()

    def test_auth_status_json(self, tmp_path):
        result = runner.invoke(
            app, ["auth", "status", "--json"],
            env={"TTCLI_AUTH_DIR": str(tmp_path)},
        )
        assert result.exit_code == 0
        assert '"authenticated": false' in result.stdout

    def test_task_help_shows_not_implemented(self):
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0

    def test_project_help_shows_not_implemented(self):
        result = runner.invoke(app, ["project", "--help"])
        assert result.exit_code == 0
