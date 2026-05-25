import pytest


@pytest.fixture
def sample_task():
    return {
        "id": "64abc123456",
        "projectId": "64def789012",
        "title": "Buy groceries",
        "content": "Milk, eggs, bread",
        "dueDate": "2026-06-01T10:00:00Z",
        "priority": 1,
        "status": "todo",
        "tags": ["personal", "shopping"],
        "timeZone": "Asia/Kolkata",
    }


@pytest.fixture
def sample_project():
    return {
        "id": "64def789012",
        "name": "Work",
        "color": "#FF0000",
        "sortOrder": 1,
        "kind": "TASK",
        "isOwner": True,
    }


@pytest.fixture
def sample_project_data(sample_project):
    return {
        **sample_project,
        "tasks": [
            {
                "id": "task1",
                "projectId": "64def789012",
                "title": "Task 1",
                "status": "todo",
            },
            {
                "id": "task2",
                "projectId": "64def789012",
                "title": "Task 2",
                "status": "doing",
            },
        ],
        "columns": [
            {"id": "col1", "name": "To Do", "sortOrder": 0},
            {"id": "col2", "name": "In Progress", "sortOrder": 1},
        ],
    }
