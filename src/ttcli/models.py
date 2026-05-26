from pydantic import BaseModel, ConfigDict


class ChecklistItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    title: str | None = None
    status: int = 0
    sortOrder: int | None = None
    startDate: str | None = None
    isAllDay: bool | None = None
    timeZone: str | None = None
    completedTime: str | None = None


class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    projectId: str | None = None
    title: str
    content: str | None = None
    desc: str | None = None
    isAllDay: bool | None = None
    startDate: str | None = None
    dueDate: str | None = None
    timeZone: str | None = None
    reminders: list | None = None
    repeatFlag: str | None = None
    priority: int = 0
    status: int = 0
    sortOrder: int | None = None
    completedTime: str | None = None
    items: list[ChecklistItem] | None = None
    tags: list[str] | None = None
    kind: str | None = None
    etag: str | None = None


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    color: str | None = None
    sortOrder: int | None = None
    kind: str | None = None
    closed: bool | None = None
    groupId: str | None = None
    viewMode: str | None = None
    isOwner: bool | None = None
