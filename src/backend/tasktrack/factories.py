"""Task construction policies shared by API writes, imports, and recurrence."""

from datetime import date
from uuid import UUID, uuid4

from tasktrack.db import now
from tasktrack.models import Task
from tasktrack.schemas import TaskInput


class TaskFactory:
    """Create validated, unsaved tasks without committing or bypassing ownership checks.

    Services authorize the list and tags before saving. Override create() for future
    approved task categories; priority remains a field, not a separate task subclass.
    """

    def create(self, account_id: str, data: TaskInput) -> Task:
        # Revalidate copied/model-constructed inputs as well as ordinary API inputs.
        values = TaskInput.model_validate(data.model_dump(include=set(TaskInput.model_fields)))
        clock = now()
        return Task(
            id=str(uuid4()),
            account_id=str(UUID(account_id)),
            list_id=str(UUID(values.list_id)),
            title=values.title,
            description=values.description,
            due_date=values.due_date,
            priority=values.priority,
            status=values.status,
            version=1,
            created_at=clock,
            updated_at=clock,
            completed_at=clock if values.status == "COMPLETED" else None,
        )

    def recurring(self, source: Task, rule_id: str, occurrence: date) -> Task:
        """Copy task details, reset progress, and preserve the deduplication key."""
        task = self.create(
            source.account_id,
            TaskInput.model_validate(
                {
                    "list_id": source.list_id,
                    "title": source.title,
                    "description": source.description,
                    "due_date": occurrence,
                    "priority": source.priority,
                }
            ),
        )
        task.recurrence_id = str(UUID(rule_id))
        task.occurrence = occurrence
        return task
