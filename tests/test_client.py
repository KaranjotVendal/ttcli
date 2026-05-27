import httpx
import pytest

from ttcli.auth import TokenData
from ttcli.client import TickTickClient, ClientError, api_client
from ttcli.models import Task, Project


@pytest.fixture
def token():
    return TokenData(
        access_token="at-123",
        refresh_token="rt-123",
        expires_in=3600,
    )


@pytest.fixture
def client(token):
    return TickTickClient(token, http_client=httpx.Client())


class TestTickTickClientInit:
    def test_sets_auth_header(self, token):
        http = httpx.Client()
        tc = TickTickClient(token, http_client=http)
        assert tc._client.headers["Authorization"] == "Bearer at-123"


class TestClientTaskMethods:
    def test_get_task(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p123/task/t456",
            method="GET",
            json={
                "id": "t456",
                "projectId": "p123",
                "title": "My Task",
                "priority": 1,
                "status": 0,
            },
        )
        task = client.get_task("p123", "t456")
        assert isinstance(task, Task)
        assert task.id == "t456"
        assert task.title == "My Task"
        assert task.status == 0

    def test_create_task(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/task",
            method="POST",
            json={
                "id": "new-task",
                "projectId": "p123",
                "title": "New Task",
                "priority": 0,
                "status": 0,
            },
        )
        task = client.create_task(Task(title="New Task", projectId="p123"))
        assert isinstance(task, Task)
        assert task.id == "new-task"

    def test_update_task(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/task/t456",
            method="POST",
            json={
                "id": "t456",
                "projectId": "p123",
                "title": "Updated",
                "priority": 3,
                "status": 0,
            },
        )
        task = client.update_task("p123", "t456", Task(title="Updated", priority=3))
        assert isinstance(task, Task)
        assert task.title == "Updated"
        assert task.priority == 3

    def test_delete_task(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p123/task/t456",
            method="DELETE",
            status_code=204,
        )
        client.delete_task("p123", "t456")  # should not raise

    def test_complete_task_returns_none_on_204(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p123/task/t456/complete",
            method="POST",
            status_code=204,
        )
        result = client.complete_task("p123", "t456")
        assert result is None

    def test_complete_task_returns_none_on_empty_200(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p123/task/t456/complete",
            method="POST",
            status_code=200,
            content=b"",
        )
        result = client.complete_task("p123", "t456")
        assert result is None

    def test_complete_task_returns_task_when_present(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p123/task/t456/complete",
            method="POST",
            json={
                "id": "t456",
                "projectId": "p123",
                "title": "Done Task",
                "status": 2,
            },
        )
        task = client.complete_task("p123", "t456")
        assert task is not None
        assert task.status == 2

    def test_list_tasks(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p123/data",
            method="GET",
            json={
                "id": "p123",
                "name": "Work",
                "tasks": [
                    {"id": "t1", "title": "Task 1", "projectId": "p123", "status": 0},
                    {"id": "t2", "title": "Task 2", "projectId": "p123", "status": 0},
                ],
            },
        )
        tasks = client.list_tasks("p123")
        assert len(tasks) == 2
        assert all(isinstance(t, Task) for t in tasks)
        assert tasks[0].title == "Task 1"

    def test_filter_tasks(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/task/filter",
            method="POST",
            json=[
                {"id": "t1", "title": "Filtered Task", "projectId": "p123", "status": 0},
            ],
        )
        result = client.filter_tasks(
            project_ids=["p123"],
            status=[0],
            priority=[1],
        )
        assert len(result) == 1
        assert result[0].title == "Filtered Task"


class TestClientProjectMethods:
    def test_list_projects(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            json=[
                {"id": "p1", "name": "Work"},
                {"id": "p2", "name": "Personal"},
            ],
        )
        projects = client.list_projects()
        assert len(projects) == 2
        assert all(isinstance(p, Project) for p in projects)
        assert projects[0].name == "Work"

    def test_get_project(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="GET",
            json={"id": "p1", "name": "Work", "color": "#FF0000"},
        )
        project = client.get_project("p1")
        assert isinstance(project, Project)
        assert project.name == "Work"

    def test_create_project(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="POST",
            json={"id": "new-p", "name": "New Project"},
        )
        project = client.create_project(Project(id="new-p", name="New Project"))
        assert isinstance(project, Project)
        assert project.name == "New Project"

    def test_update_project(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="POST",
            json={"id": "p1", "name": "Updated", "color": "#00FF00"},
        )
        project = client.update_project("p1", Project(id="p1", name="Updated"))
        assert project.name == "Updated"

    def test_delete_project(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1",
            method="DELETE",
            status_code=204,
        )
        client.delete_project("p1")

    def test_get_project_data(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p1/data",
            method="GET",
            json={
                "project": {"id": "p1", "name": "Work"},
                "tasks": [
                    {"id": "t1", "title": "Task", "projectId": "p1", "status": 0}
                ],
                "columns": [
                    {"id": "c1", "name": "To Do", "sortOrder": 0},
                ],
            },
        )
        data = client.get_project_data("p1")
        assert data["project"]["id"] == "p1"
        assert len(data["tasks"]) == 1
        assert len(data["columns"]) == 1


class TestClientAuthRefresh:
    def test_refreshes_token_on_401(self, token, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            status_code=401,
            json={"error": "token_expired"},
        )
        httpx_mock.add_response(
            url="https://api.ticktick.com/oauth/token",
            method="POST",
            json={
                "access_token": "new-at",
                "refresh_token": "new-rt",
                "expires_in": 3600,
            },
        )
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            json=[{"id": "p1", "name": "Work"}],
        )

        http = httpx.Client()
        tc = TickTickClient(token, client_id="cid", client_secret="cs", http_client=http)
        projects = tc.list_projects()
        assert len(projects) == 1
        assert tc._token.access_token == "new-at"

    def test_raises_client_error_on_non_401(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            status_code=500,
            json={"message": "Internal error"},
        )
        with pytest.raises(ClientError):
            client.list_projects()

    def test_raises_client_error_on_404(self, client, httpx_mock):
        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project/p404",
            method="GET",
            status_code=404,
            json={"message": "Not found"},
        )
        with pytest.raises(ClientError):
            client.get_project("p404")


class TestApiClientContextManager:
    def test_api_client_loads_token_and_creates_client(self, httpx_mock, tmp_path):
        from ttcli.auth import save_tokens, TokenData

        token = TokenData(access_token="at", refresh_token="rt", expires_in=3600)
        save_tokens(token, tmp_path)

        httpx_mock.add_response(
            url="https://api.ticktick.com/open/v1/project",
            method="GET",
            json=[],
        )

        with api_client(client_id="cid", client_secret="cs", storage_dir=tmp_path) as tc:
            assert isinstance(tc, TickTickClient)
            projects = tc.list_projects()
            assert projects == []
