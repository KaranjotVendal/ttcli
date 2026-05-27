from pathlib import Path

import pytest
from typer.testing import CliRunner

from ttcli.auth import save_tokens, TokenData
from ttcli.main import app

runner = CliRunner()


@pytest.fixture
def authed_env(tmp_path):
    """Set up a valid auth token in a temp dir and return the env dict."""
    token = TokenData(access_token="at-1", refresh_token="rt-1", expires_in=3600)
    save_tokens(token, tmp_path)
    return {"TTCLI_AUTH_DIR": str(tmp_path)}


class TestTaskCli:
    def test_list(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/data",
            method="GET",
            json={
                "id": "p1",
                "name": "Project",
                "tasks": [
                    {"id": "t1", "title": "Task 1", "projectId": "p1", "status": 0},
                    {"id": "t2", "title": "Task 2", "projectId": "p1", "status": 2},
                ],
            },
        )
        result = runner.invoke(app, ["task", "list", "--project-id", "p1"], env=authed_env)
        assert result.exit_code == 0
        assert "Task 1" in result.stdout
        assert "Task 2" in result.stdout

    def test_list_json(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/data",
            method="GET",
            json={
                "id": "p1",
                "name": "Project",
                "tasks": [
                    {"id": "t1", "title": "Task 1", "projectId": "p1", "status": 0},
                ],
            },
        )
        result = runner.invoke(
            app, ["task", "list", "--project-id", "p1", "--json"], env=authed_env
        )
        assert result.exit_code == 0
        assert '"title": "Task 1"' in result.stdout

    def test_get(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/task/t1",
            method="GET",
            json={"id": "t1", "projectId": "p1", "title": "My Task", "priority": 3, "status": 0},
        )
        result = runner.invoke(
            app, ["task", "get", "t1", "--project-id", "p1"], env=authed_env
        )
        assert result.exit_code == 0
        assert "My Task" in result.stdout

    def test_get_json(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/task/t1",
            method="GET",
            json={"id": "t1", "projectId": "p1", "title": "My Task", "status": 0},
        )
        result = runner.invoke(
            app, ["task", "get", "t1", "--project-id", "p1", "--json"], env=authed_env
        )
        assert result.exit_code == 0
        assert '"title": "My Task"' in result.stdout

    def test_create(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/task",
            method="POST",
            json={"id": "new-t1", "projectId": "p1", "title": "Created Task", "status": 0},
        )
        result = runner.invoke(
            app, ["task", "create", "Created Task", "--project-id", "p1"], env=authed_env
        )
        assert result.exit_code == 0
        assert "Created Task" in result.stdout

    def test_update(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/task/t1",
            method="GET",
            json={"id": "t1", "projectId": "p1", "title": "Old", "status": 0},
        )
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/task/t1",
            method="POST",
            json={"id": "t1", "projectId": "p1", "title": "Updated Title", "status": 0, "priority": 3},
        )
        result = runner.invoke(
            app, ["task", "update", "t1", "--project-id", "p1", "--title", "Updated Title", "--priority", "3"],
            env=authed_env,
        )
        assert result.exit_code == 0
        assert "Updated Title" in result.stdout

    def test_delete(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/task/t1",
            method="DELETE",
            status_code=204,
        )
        result = runner.invoke(
            app, ["task", "delete", "t1", "--project-id", "p1"], env=authed_env
        )
        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()

    def test_complete(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/task/t1/complete",
            method="POST",
            status_code=204,
        )
        result = runner.invoke(
            app, ["task", "complete", "t1", "--project-id", "p1"], env=authed_env
        )
        assert result.exit_code == 0
        assert "completed" in result.stdout.lower()

    def test_filter(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/task/filter",
            method="POST",
            json=[
                {"id": "t1", "projectId": "p1", "title": "Filtered", "status": 0},
            ],
        )
        result = runner.invoke(
            app, ["task", "filter", "--project-ids", "p1", "--status", "0"],
            env=authed_env,
        )
        assert result.exit_code == 0
        assert "Filtered" in result.stdout

    def test_error_when_not_authenticated(self):
        result = runner.invoke(
            app, ["task", "list", "--project-id", "p1"],
            env={"TTCLI_AUTH_DIR": "/nonexistent"},
        )
        assert result.exit_code != 0


class TestProjectCli:
    def test_list(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            json=[
                {"id": "p1", "name": "Work"},
                {"id": "p2", "name": "Personal"},
            ],
        )
        result = runner.invoke(app, ["project", "list"], env=authed_env)
        assert result.exit_code == 0
        assert "Work" in result.stdout
        assert "Personal" in result.stdout

    def test_list_json(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            json=[
                {"id": "p1", "name": "Work"},
            ],
        )
        result = runner.invoke(app, ["project", "list", "--json"], env=authed_env)
        assert result.exit_code == 0
        assert '"name": "Work"' in result.stdout

    def test_get(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="GET",
            json={"id": "p1", "name": "Work", "color": "#FF0000", "kind": "TASK"},
        )
        result = runner.invoke(app, ["project", "get", "p1"], env=authed_env)
        assert result.exit_code == 0
        assert "Work" in result.stdout

    def test_create(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="POST",
            json={"id": "new-p", "name": "New Project"},
        )
        result = runner.invoke(app, ["project", "create", "New Project"], env=authed_env)
        assert result.exit_code == 0
        assert "New Project" in result.stdout

    def test_update(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="GET",
            json={"id": "p1", "name": "Old Name"},
        )
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="POST",
            json={"id": "p1", "name": "Updated Project"},
        )
        result = runner.invoke(
            app, ["project", "update", "p1", "--name", "Updated Project"], env=authed_env
        )
        assert result.exit_code == 0
        assert "Updated Project" in result.stdout

    def test_delete(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="DELETE",
            status_code=204,
        )
        result = runner.invoke(app, ["project", "delete", "p1"], env=authed_env)
        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()

    def test_data(self, authed_env, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/data",
            method="GET",
            json={
                "project": {"id": "p1", "name": "Work"},
                "tasks": [{"id": "t1", "title": "Task 1", "projectId": "p1", "status": 0}],
                "columns": [{"id": "c1", "name": "To Do", "sortOrder": 0}],
            },
        )
        result = runner.invoke(app, ["project", "data", "p1"], env=authed_env)
        assert result.exit_code == 0
        assert "Task 1" in result.stdout
        assert "To Do" in result.stdout
        assert "Work" in result.stdout
