import pytest
from pydantic import ValidationError

from ttcli.models import Task, Project, ChecklistItem


class TestChecklistItem:
    def test_create_with_title(self):
        item = ChecklistItem(title="Subtask 1")
        assert item.title == "Subtask 1"
        assert item.status == 0

    def test_create_with_all_fields(self):
        item = ChecklistItem(
            id="item1",
            title="Subtask",
            status=0,
            sortOrder=1,
            startDate="2019-11-13T03:00:00+0000",
            isAllDay=False,
            timeZone="America/Los_Angeles",
            completedTime="2019-11-13T03:00:00+0000",
        )
        assert item.id == "item1"
        assert item.status == 0
        assert item.isAllDay is False

    def test_unknown_fields_ignored(self):
        item = ChecklistItem(**{"title": "Test", "bogus": "ignored"})
        assert item.title == "Test"
        assert not hasattr(item, "bogus")


class TestTask:
    def test_create_with_title_only(self):
        task = Task(title="Buy groceries")
        assert task.title == "Buy groceries"
        assert task.priority == 0
        assert task.status == 0
        assert task.content is None
        assert task.id is None
        assert task.projectId is None

    def test_create_with_all_fields(self):
        task = Task(
            id="64abc123456",
            projectId="64def789012",
            title="Buy groceries",
            content="Milk, eggs, bread",
            desc="Checklist description",
            isAllDay=False,
            startDate="2019-11-13T03:00:00+0000",
            dueDate="2019-11-14T03:00:00+0000",
            timeZone="America/Los_Angeles",
            reminders=["TRIGGER:P0DT9H0M0S"],
            repeatFlag="RRULE:FREQ=DAILY;INTERVAL=1",
            priority=1,
            status=0,
            sortOrder=12345,
            completedTime="2019-11-13T03:00:00+0000",
            tags=["personal", "shopping"],
            kind="TEXT",
            etag="abc123",
        )
        assert task.id == "64abc123456"
        assert task.title == "Buy groceries"
        assert task.desc == "Checklist description"
        assert task.isAllDay is False
        assert task.startDate == "2019-11-13T03:00:00+0000"
        assert task.repeatFlag == "RRULE:FREQ=DAILY;INTERVAL=1"
        assert task.status == 0
        assert task.sortOrder == 12345
        assert task.kind == "TEXT"
        assert task.etag == "abc123"

    def test_create_with_items(self):
        task = Task(
            title="With subtasks",
            items=[
                ChecklistItem(title="Sub 1", status=0),
                ChecklistItem(title="Sub 2", status=1),
            ],
        )
        assert len(task.items) == 2
        assert task.items[0].title == "Sub 1"
        assert task.items[1].status == 1

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
            closed=False,
            groupId="group1",
            viewMode="list",
            isOwner=True,
        )
        assert project.id == "64def789012"
        assert project.name == "Work"
        assert project.color == "#FF0000"
        assert project.sortOrder == 1
        assert project.kind == "TASK"
        assert project.closed is False
        assert project.groupId == "group1"
        assert project.viewMode == "list"
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
