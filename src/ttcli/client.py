from contextlib import contextmanager

import httpx

from ttcli.auth import (
    TokenData,
    load_tokens,
    refresh_access_token,
    is_authenticated,
    AuthError,
)
from ttcli.models import Task, Project

BASE_URL = "https://api.ticktick.com/open/v1"


class ClientError(Exception):
    pass


class TickTickClient:
    """HTTP client for TickTick Open API.

    Wraps httpx.Client with auth headers, automatic token refresh on 401,
    and typed methods for all Task and Project endpoints.
    """

    def __init__(
        self,
        token: TokenData,
        client_id: str | None = None,
        client_secret: str | None = None,
        http_client: httpx.Client | None = None,
    ):
        self._token = token
        self._client_id = client_id
        self._client_secret = client_secret
        self._client = http_client or httpx.Client()
        self._client.headers["Authorization"] = f"Bearer {token.access_token}"

    # ------------------------------------------------------------------
    # Task endpoints
    # ------------------------------------------------------------------

    def get_task(self, project_id: str, task_id: str) -> Task:
        data = self._request("GET", f"/project/{project_id}/task/{task_id}")
        return Task(**data)

    def create_task(self, task: Task) -> Task:
        data = self._request(
            "POST",
            "/task",
            json=task.model_dump(exclude_none=True),
        )
        return Task(**data)

    def update_task(self, project_id: str, task_id: str, task: Task) -> Task:
        payload = task.model_dump(exclude_none=True)
        payload["id"] = task_id
        payload["projectId"] = project_id
        data = self._request("POST", f"/task/{task_id}", json=payload)
        return Task(**data)

    def delete_task(self, project_id: str, task_id: str) -> None:
        self._request("DELETE", f"/project/{project_id}/task/{task_id}")

    def complete_task(self, project_id: str, task_id: str) -> Task | None:
        data = self._request(
            "POST", f"/project/{project_id}/task/{task_id}/complete"
        )
        if data:
            return Task(**data)
        return None

    def list_tasks(self, project_id: str) -> list[Task]:
        data = self._request("GET", f"/project/{project_id}/data")
        tasks = data.get("tasks", [])
        return [Task(**t) for t in tasks]

    def filter_tasks(
        self,
        project_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        priority: list[int] | None = None,
        tag: list[str] | None = None,
        status: list[int] | None = None,
    ) -> list[Task]:
        payload: dict = {}
        if project_ids is not None:
            payload["projectIds"] = project_ids
        if start_date is not None:
            payload["startDate"] = start_date
        if end_date is not None:
            payload["endDate"] = end_date
        if priority is not None:
            payload["priority"] = priority
        if tag is not None:
            payload["tag"] = tag
        if status is not None:
            payload["status"] = status
        data = self._request("POST", "/task/filter", json=payload)
        return [Task(**t) for t in data]

    # ------------------------------------------------------------------
    # Project endpoints
    # ------------------------------------------------------------------

    def list_projects(self) -> list[Project]:
        data = self._request("GET", "/project")
        return [Project(**p) for p in data]

    def get_project(self, project_id: str) -> Project:
        data = self._request("GET", f"/project/{project_id}")
        return Project(**data)

    def create_project(self, project: Project) -> Project:
        data = self._request(
            "POST",
            "/project",
            json=project.model_dump(exclude_none=True),
        )
        return Project(**data)

    def update_project(self, project_id: str, project: Project) -> Project:
        payload = project.model_dump(exclude_none=True)
        payload["id"] = project_id
        data = self._request("POST", f"/project/{project_id}", json=payload)
        return Project(**data)

    def delete_project(self, project_id: str) -> None:
        self._request("DELETE", f"/project/{project_id}")

    def get_project_data(self, project_id: str) -> dict:
        return self._request("GET", f"/project/{project_id}/data")

    # ------------------------------------------------------------------
    # Internal request handling
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        """Make an HTTP request with automatic token refresh on 401."""
        url = f"{BASE_URL}{path}"
        for attempt in range(2):
            resp = self._client.request(method, url, **kwargs)
            if resp.status_code == 401 and attempt == 0:
                if self._client_id and self._client_secret:
                    self._refresh_token()
                    continue
                raise ClientError(
                    "Token rejected by API. Run 'ttcli auth refresh' or 'ttcli auth setup' to re-authenticate."
                )
            if resp.status_code >= 400:
                body = self._safe_json(resp)
                msg = body.get("message", body.get("error", resp.text))
                raise ClientError(f"HTTP {resp.status_code}: {msg}")
            if resp.status_code == 204 or not resp.content.strip():
                return {}
            return resp.json()
        return {}  # unreachable

    def _refresh_token(self) -> None:
        """Refresh the access token and update auth headers."""
        if not self._client_id or not self._client_secret:
            raise ClientError("Cannot refresh token: no client_id/client_secret")
        self._token = refresh_access_token(
            self._token.refresh_token,
            self._client_id,
            self._client_secret,
            http_client=self._client,
        )
        self._client.headers["Authorization"] = f"Bearer {self._token.access_token}"

    @staticmethod
    def _safe_json(resp: httpx.Response) -> dict:
        try:
            return resp.json()
        except Exception:
            return {}


@contextmanager
def api_client(
    client_id: str | None = None,
    client_secret: str | None = None,
    storage_dir=None,
) -> TickTickClient:
    """Context manager that loads stored tokens and creates a TickTickClient.

    Usage:
        with api_client() as client:
            projects = client.list_projects()
    """
    token = load_tokens(storage_dir)
    if token is None:
        raise ClientError("Not authenticated. Run 'ttcli auth setup' first.")
    if token.is_expired:
        if not client_id or not client_secret:
            raise ClientError(
                "Token expired. Provide client_id/client_secret or run 'ttcli auth refresh'."
            )
        token = refresh_access_token(
            token.refresh_token, client_id, client_secret, storage_dir=storage_dir
        )
    http = httpx.Client(base_url=BASE_URL)
    try:
        yield TickTickClient(
            token,
            client_id=client_id,
            client_secret=client_secret,
            http_client=http,
        )
    finally:
        http.close()
