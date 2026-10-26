"""Account-scoped task query construction; HTTP and pagination remain in the API."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import Select, select

from tasktrack.models import Task, TaskTag
from tasktrack.schemas import Priority, Status


@dataclass(frozen=True)
class TaskFilter:
    q: str = ""
    list_id: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    tag_id: str | None = None
    due: Literal["today", "upcoming", "overdue", "undated"] | None = None
    due_from: date | None = None
    due_through: date | None = None
    trashed: bool = False

    def __post_init__(self) -> None:
        if self.due_from and self.due_through and self.due_from > self.due_through:
            raise ValueError("Start date must not follow end date")

    def query(self, account_id: str, today: date, clock: datetime) -> Select[Task]:
        query = select(Task).where(Task.account_id == account_id)
        query = (
            query.where(Task.deleted_at.is_not(None), Task.purge_after > clock)
            if self.trashed
            else query.where(Task.deleted_at.is_(None))
        )
        for column, value in (
            (Task.list_id, self.list_id),
            (Task.status, self.status),
            (Task.priority, self.priority),
        ):
            if value:
                query = query.where(column == value)
        if self.q:
            escaped = self.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(Task.title.ilike("%" + escaped + "%", escape="\\"))
        if self.tag_id:
            query = query.where(
                Task.id.in_(
                    select(TaskTag.task_id).where(
                        TaskTag.account_id == account_id, TaskTag.tag_id == self.tag_id
                    )
                )
            )
        if self.due == "today":
            query = query.where(Task.due_date == today)
        elif self.due == "upcoming":
            query = query.where(Task.due_date > today)
        elif self.due == "overdue":
            query = query.where(Task.due_date < today, Task.status != "COMPLETED")
        elif self.due == "undated":
            query = query.where(Task.due_date.is_(None))
        if self.due_from:
            query = query.where(Task.due_date >= self.due_from)
        if self.due_through:
            query = query.where(Task.due_date <= self.due_through)
        return query
