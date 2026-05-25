from pydantic import BaseModel, ConfigDict


class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    projectId: str | None = None
    title: str
    content: str | None = None
    dueDate: str | None = None
    priority: int = 0
    status: str = "todo"
    tags: list[str] | None = None
    timeZone: str | None = None
    reminders: list | None = None


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    color: str | None = None
    sortOrder: int | None = None
    kind: str | None = None
    isOwner: bool | None = None
