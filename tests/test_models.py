import pytest
from pydantic import ValidationError

from ttcli.models import Task, Project


class TestTask:
    def test_create_with_title_only(self):
        task = Task(title="Buy groceries")
        assert task.title == "Buy groceries"
        assert task.priority == 0
        assert task.status == "todo"
        assert task.content is None
        assert task.id is None
        assert task.projectId is None

    def test_create_with_all_fields(self):
        task = Task(
            id="64abc123456",
            projectId="64def789012",
            title="Buy groceries",
            content="Milk, eggs, bread",
            dueDate="2026-06-01T10:00:00Z",
            priority=1,
            status="todo",
            tags=["personal", "shopping"],
            timeZone="Asia/Kolkata",
        )
        assert task.id == "64abc123456"
        assert task.projectId == "64def789012"
        assert task.title == "Buy groceries"
        assert task.content == "Milk, eggs, bread"
        assert task.dueDate == "2026-06-01T10:00:00Z"
        assert task.priority == 1
        assert task.status == "todo"
        assert task.tags == ["personal", "shopping"]
        assert task.timeZone == "Asia/Kolkata"

    def test_serialize_excludes_none_fields(self):
        task = Task(
            id="64abc123456",
            projectId="64def789012",
            title="Buy groceries",
            priority=1,
        )
        data = task.model_dump(exclude_none=True)
        assert data["title"] == "Buy groceries"
        assert data["priority"] == 1
        assert "content" not in data
        assert "tags" not in data
        assert "reminders" not in data

    def test_json_round_trip(self):
        task = Task(
            id="64abc123456",
            title="Buy groceries",
            priority=1,
            tags=["personal"],
        )
        json_str = task.model_dump_json(exclude_none=True)
        restored = Task.model_validate_json(json_str)
        assert restored.id == task.id
        assert restored.title == task.title
        assert restored.priority == task.priority
        assert restored.tags == task.tags

    def test_unknown_fields_ignored(self):
        task = Task(**{"title": "Test", "bogus_field": "should be ignored"})
        assert task.title == "Test"
        assert not hasattr(task, "bogus_field")

    def test_title_is_required(self):
        with pytest.raises(ValidationError):
            Task()


class TestProject:
    def test_create_with_all_fields(self):
        project = Project(
            id="64def789012",
            name="Work",
            color="#FF0000",
            sortOrder=1,
            kind="TASK",
            isOwner=True,
        )
        assert project.id == "64def789012"
        assert project.name == "Work"
        assert project.color == "#FF0000"
        assert project.sortOrder == 1
        assert project.kind == "TASK"
        assert project.isOwner is True

    def test_json_round_trip(self):
        project = Project(id="abc123", name="Work", color="#FF0000")
        json_str = project.model_dump_json(exclude_none=True)
        restored = Project.model_validate_json(json_str)
        assert restored.id == project.id
        assert restored.name == project.name
        assert restored.color == project.color

    def test_unknown_fields_ignored(self):
        project = Project(**{"id": "x", "name": "Test", "bogus": "ignored"})
        assert project.name == "Test"
        assert not hasattr(project, "bogus")

    def test_id_is_required(self):
        with pytest.raises(ValidationError):
            Project(name="No ID")

    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            Project(id="abc")
