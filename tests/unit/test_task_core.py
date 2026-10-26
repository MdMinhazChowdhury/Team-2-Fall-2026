"""Person C core tests: no network, database, worker, or frontend is required."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from tasktrack import services
from tasktrack.factories import TaskFactory
from tasktrack.filters import TaskFilter
from tasktrack.schemas import TaskInput

ACCOUNT = str(uuid4())
LIST = str(uuid4())


def test_factory_defaults_and_unique_ids(monkeypatch):
    clock = datetime(2026, 10, 25, 12, tzinfo=UTC)
    monkeypatch.setattr("tasktrack.factories.now", lambda: clock)
    first = TaskFactory().create(ACCOUNT, TaskInput(list_id=LIST, title="  Essay  "))
    second = TaskFactory().create(ACCOUNT, TaskInput(list_id=LIST, title="Essay"))
    assert first.id != second.id and str(UUID(first.id)) == first.id
    assert (first.account_id, first.list_id, first.title) == (ACCOUNT, LIST, "Essay")
    assert (first.priority, first.status, first.description) == ("MEDIUM", "TODO", "")
    assert first.version == 1 and first.completed_at is None and first.due_date is None
    assert first.created_at == first.updated_at == clock


@pytest.mark.parametrize("title", ["", " ", "\t\n", None, "x" * 201])
def test_factory_rejects_invalid_title_even_if_input_was_modified(title):
    data = TaskInput(list_id=LIST, title="Valid").model_copy(update={"title": title})
    with pytest.raises(ValidationError):
        TaskFactory().create(ACCOUNT, data)


@pytest.mark.parametrize("length", [1, 200])
def test_title_boundaries(length):
    assert (
        len(TaskFactory().create(ACCOUNT, TaskInput(list_id=LIST, title="x" * length)).title)
        == length
    )


@pytest.mark.parametrize("length,valid", [(5000, True), (5001, False)])
def test_description_boundary(length, valid):
    data = TaskInput(list_id=LIST, title="Task").model_copy(update={"description": "x" * length})
    if valid:
        assert len(TaskFactory().create(ACCOUNT, data).description) == length
    else:
        with pytest.raises(ValidationError):
            TaskFactory().create(ACCOUNT, data)


@pytest.mark.parametrize("priority", ["LOW", "MEDIUM", "HIGH"])
def test_priority_creation_policy(priority):
    task = TaskFactory().create(ACCOUNT, TaskInput(list_id=LIST, title="Task", priority=priority))
    assert task.priority == priority


@pytest.mark.parametrize("field,value", [("priority", "URGENT"), ("status", "NOT_STARTED")])
def test_rejects_values_outside_the_web_contract(field, value):
    data = TaskInput(list_id=LIST, title="Task").model_copy(update={field: value})
    with pytest.raises(ValidationError):
        TaskFactory().create(ACCOUNT, data)


def test_completed_task_and_recurring_instance_have_separate_state():
    factory = TaskFactory()
    source = factory.create(
        ACCOUNT,
        TaskInput(list_id=LIST, title="Repeat", priority="HIGH", status="COMPLETED"),
    )
    rule = str(uuid4())
    occurrence = date(2026, 10, 26)
    generated = factory.recurring(source, rule, occurrence)
    assert source.status == "COMPLETED" and source.completed_at is not None
    assert generated.id != source.id and generated.status == "TODO"
    assert generated.completed_at is None and generated.priority == "HIGH"
    assert generated.recurrence_id == rule and generated.occurrence == occurrence
    assert generated.due_date == occurrence and generated.account_id == source.account_id


@pytest.mark.parametrize("deadline", [None, date(2000, 1, 1), date(2026, 10, 25)])
def test_absent_past_and_current_deadlines_are_preserved(deadline):
    task = TaskFactory().create(ACCOUNT, TaskInput(list_id=LIST, title="Task", due_date=deadline))
    assert task.due_date == deadline


def test_bad_identifiers_cannot_create_tasks():
    with pytest.raises(ValueError):
        TaskFactory().create("not-a-uuid", TaskInput(list_id=LIST, title="Task"))
    with pytest.raises(ValueError):
        TaskFactory().create(ACCOUNT, TaskInput(list_id="not-a-uuid", title="Task"))


def test_date_range_boundary_and_reversed_range():
    day = date(2026, 10, 25)
    assert TaskFilter(due_from=day, due_through=day).due_from == day
    with pytest.raises(ValueError, match="Start date"):
        TaskFilter(due_from=date(2026, 10, 26), due_through=day)


class SessionStub:
    """Record service writes without pretending to implement persistence."""

    def __init__(self):
        self.added = []
        self.flushed = 0

    def add(self, value):
        self.added.append(value)

    def execute(self, statement):
        pass

    def flush(self):
        self.flushed += 1


def test_service_uses_injected_factory_with_stub(monkeypatch):
    class RecordingFactory(TaskFactory):
        calls = 0

        def create(self, account_id, data):
            self.calls += 1
            return super().create(account_id, data)

    monkeypatch.setattr(services, "owned", lambda *args, **kwargs: object())
    monkeypatch.setattr(services, "event", lambda *args: None)
    db = SessionStub()
    factory = RecordingFactory()
    task = services.save_task(db, ACCOUNT, TaskInput(list_id=LIST, title="Task"), factory=factory)
    assert factory.calls == 1 and db.added == [task] and db.flushed == 2


def test_missing_or_foreign_list_is_rejected_before_factory_or_writes(monkeypatch):
    def reject(*args, **kwargs):
        raise HTTPException(404, "Item not found")

    monkeypatch.setattr(services, "owned", reject)
    db = SessionStub()
    with pytest.raises(HTTPException) as failure:
        services.save_task(db, ACCOUNT, TaskInput(list_id=LIST, title="Task"))
    assert failure.value.status_code == 404 and not db.added and db.flushed == 0
