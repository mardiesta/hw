from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

# Типы полей с ограничениями длины, совпадающими с колонками в БД.
Email = Annotated[EmailStr, Field(max_length=255)]
Name255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Title200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Name64 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
ColorHex = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

UserRole = Literal["operator", "admin"]
TaskStatus = Literal["open", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


class _InputModel(BaseModel):
    # Служебные поля (id, created_at, updated_at) и любые лишние поля отклоняются с 422.
    model_config = ConfigDict(extra="forbid")


class _ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- users ----------

class UserCreate(_InputModel):
    email: Email
    display_name: Name255
    role: UserRole = "operator"


class UserUpdate(_InputModel):
    email: Email | None = None
    display_name: Name255 | None = None
    role: UserRole | None = None


class UserRead(_ReadModel):
    id: int
    email: str
    display_name: str
    role: str
    created_at: datetime


# ---------- projects ----------

class ProjectCreate(_InputModel):
    name: Title200
    description: str | None = None


class ProjectUpdate(_InputModel):
    name: Title200 | None = None
    description: str | None = None


class ProjectRead(_ReadModel):
    id: int
    name: str
    description: str | None
    created_at: datetime


# ---------- labels ----------

class LabelCreate(_InputModel):
    name: Name64
    color: ColorHex = "#6b7280"


class LabelUpdate(_InputModel):
    name: Name64 | None = None
    color: ColorHex | None = None


class LabelRead(_ReadModel):
    id: int
    name: str
    color: str


# ---------- tasks ----------

class TaskCreate(_InputModel):
    project_id: int
    assignee_id: int | None = None
    label_id: int | None = None
    title: Title200
    description: str | None = None
    status: TaskStatus = "open"
    priority: TaskPriority = "medium"


class TaskUpdate(_InputModel):
    project_id: int | None = None
    assignee_id: int | None = None
    label_id: int | None = None
    title: Title200 | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskRead(_ReadModel):
    id: int
    project_id: int
    assignee_id: int | None
    label_id: int | None
    title: str
    description: str | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime


# ---------- comments ----------

class CommentCreate(_InputModel):
    task_id: int
    author_id: int
    body: NonEmptyText


class CommentUpdate(_InputModel):
    task_id: int | None = None
    author_id: int | None = None
    body: NonEmptyText | None = None


class CommentRead(_ReadModel):
    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime
