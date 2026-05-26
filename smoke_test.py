#!/usr/bin/env python3
"""Smoke test for the TickTick API.

Uses OAuth2 authorization code flow with local web server (no copy-paste).
Tests: auth, list projects, create task, get task, update task, complete task, delete task.
"""

import sys

from ttcli.auth import authenticate_local_server, save_tokens
from ttcli.client import TickTickClient
from ttcli.models import Task, Project

CLIENT_ID = "H3rkl7DrqQF940bCOt"
CLIENT_SECRET = "8Ob36h9A3KZ48WW2ZrYzeu43jFpeEGv2"


def step(label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def ok(label: str):
    print(f"  ✅ {label}")


def main():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     TickTick API Smoke Test                  ║")
    print("  ╚══════════════════════════════════════════════╝")

    # ------------------------------------------------------------------
    # Step 1: Authenticate (local web server, no copy-paste)
    # ------------------------------------------------------------------
    step("1/7 — Authenticate via local web server")

    token = authenticate_local_server(CLIENT_ID, CLIENT_SECRET)
    ok(f"Token obtained (access: {token.access_token[:20]}...)")

    import httpx
    http = httpx.Client()
    client = TickTickClient(token, http_client=http)

    # ------------------------------------------------------------------
    # Step 2: List projects
    # ------------------------------------------------------------------
    step("2/7 — List projects")

    projects = client.list_projects()
    if not projects:
        print("  ❌ No projects found. Create at least one project in TickTick first.")
        sys.exit(1)

    ok(f"Found {len(projects)} project(s)")
    for p in projects[:5]:
        print(f"     - {p.name}")
    if len(projects) > 5:
        print(f"     ... and {len(projects) - 5} more")

    project_id = projects[0].id

    # ------------------------------------------------------------------
    # Step 3: Create a task
    # ------------------------------------------------------------------
    step("3/7 — Create a task")

    task = Task(
        title="[ttcli smoke test] Hello from API",
        content="Created by the smoke test script.",
        projectId=project_id,
        priority=1,
    )
    created = client.create_task(task)
    ok(f"Task created: '{created.title}' (id={created.id})")
    task_id = created.id

    # ------------------------------------------------------------------
    # Step 4: Get the task
    # ------------------------------------------------------------------
    step("4/7 — Get task by ID")

    fetched = client.get_task(project_id, task_id)
    assert fetched.id == task_id
    assert fetched.title == task.title
    ok(f"Task retrieved: '{fetched.title}' (status={fetched.status})")

    # ------------------------------------------------------------------
    # Step 5: Update the task
    # ------------------------------------------------------------------
    step("5/7 — Update task")

    fetched.title = "[ttcli smoke test] Updated title"
    fetched.content = "Updated content from smoke test."
    fetched.priority = 3
    updated = client.update_task(project_id, task_id, fetched)
    assert updated.title == "[ttcli smoke test] Updated title"
    ok(f"Task updated: '{updated.title}' (priority={updated.priority})")

    # ------------------------------------------------------------------
    # Step 6: Complete the task
    # ------------------------------------------------------------------
    step("6/7 — Complete task")

    result = client.complete_task(project_id, task_id)
    if result is not None:
        ok(f"Task completed (status={result.status})")
    else:
        ok("Task completed (empty response)")

    # ------------------------------------------------------------------
    # Step 7: Delete the task
    # ------------------------------------------------------------------
    step("7/7 — Delete task")

    client.delete_task(project_id, task_id)
    ok("Task deleted")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  ✅ All smoke tests passed!")
    print(f"{'='*60}")
    print(f"\n  Token saved to ~/.ttcli/auth.json — you can now use 'ttcli' commands.\n")

    http.close()


if __name__ == "__main__":
    main()
