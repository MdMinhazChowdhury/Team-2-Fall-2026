"""Construction policies shared by account and task workflows."""

from datetime import date, datetime
from uuid import UUID, uuid4

from tasktrack.db import now
from tasktrack.models import Account, Task
from tasktrack.schemas import TaskInput


class AccountFactory:
    """Create validated, unsaved accounts for registration and administration."""

    roles = frozenset({"USER", "ADMIN"})

    def create(
        self,
        email: str,
        password_hash: str,
        role: str = "USER",
        *,
        verified_at: datetime | None = None,
    ) -> Account:
        normalized_email = email.strip().casefold()
        normalized_role = role.strip().upper() if role else ""
        if not normalized_email:
            raise ValueError("Email is required")
        if not password_hash:
            raise ValueError("Password hash is required")
        if normalized_role not in self.roles:
            raise ValueError(f"Unknown account role: {role}")
        return Account(
            id=str(uuid4()),
            email=normalized_email,
            password_hash=password_hash,
            role=normalized_role,
            active=True,
            verified_at=verified_at,
            created_at=now(),
        )


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
