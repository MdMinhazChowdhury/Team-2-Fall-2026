"""Regression checks for the Java-to-web core alignment against real PostgreSQL."""

from datetime import UTC, date, datetime

import pytest
from conftest import create_list, create_task, payload, send
from tasktrack.factories import TaskFactory
from tasktrack.jobs import run_due


def test_task_api_uses_factory_without_changing_frontend_contract(auth, monkeypatch):
    calls = []
    original = TaskFactory.create

    def record(self, account_id, data):
        task = original(self, account_id, data)
        calls.append(task.id)
        return task

    monkeypatch.setattr(TaskFactory, "create", record)
    task = create_task(auth, create_list(auth)["id"], title="  My task  ")
    assert calls == [task["id"]]
    assert (task["title"], task["status"], task["priority"], task["version"]) == (
        "My task",
        "TODO",
        "MEDIUM",
        1,
    )


def test_combined_filters_are_inclusive_and_account_scoped(auth):
    first = create_list(auth)
    second = create_list(auth, "Other")
    tag = send(auth, "POST", "/tags", {"name": "School"}).json()["id"]
    selected = create_task(
        auth,
        first["id"],
        title="Selected",
        due_date="2026-10-25",
        priority="HIGH",
        status="IN_PROGRESS",
        tag_ids=[tag],
    )
    for values in [
        {"due_date": "2026-10-24", "priority": "HIGH", "status": "IN_PROGRESS"},
        {"due_date": "2026-10-26", "priority": "HIGH", "status": "IN_PROGRESS"},
        {"priority": "HIGH", "status": "IN_PROGRESS"},
        {"due_date": "2026-10-25", "priority": "LOW", "status": "IN_PROGRESS"},
        {"due_date": "2026-10-25", "priority": "HIGH", "status": "TODO"},
    ]:
        create_task(auth, first["id"], tag_ids=[tag], **values)
    create_task(
        auth,
        second["id"],
        due_date="2026-10-25",
        priority="HIGH",
        status="IN_PROGRESS",
        tag_ids=[tag],
    )
    response = auth.get(
        "/api/tasks",
        params={
            "list_id": first["id"],
            "tag_id": tag,
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "due_from": "2026-10-25",
            "due_through": "2026-10-25",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [task["id"] for task in response.json()["items"]] == [selected["id"]]


@pytest.mark.parametrize("q,title", [("%", "100% done"), ("_", "task_name"), ("\\", "a\\b")])
def test_search_treats_sql_wildcards_as_literal_text(auth, q, title):
    task_list = create_list(auth)
    match = create_task(auth, task_list["id"], title=title)
    create_task(auth, task_list["id"], title="Unrelated")
    result = auth.get("/api/tasks", params={"q": q}).json()
    assert [row["id"] for row in result["items"]] == [match["id"]]


def test_filter_pagination_and_empty_results(auth):
    task_list = create_list(auth)
    dated = create_task(auth, task_list["id"], due_date="2026-10-25")
    undated = create_task(auth, task_list["id"])
    first = auth.get("/api/tasks?page_size=1&page=1").json()
    second = auth.get("/api/tasks?page_size=1&page=2").json()
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["id"] == dated["id"]
    assert second["items"][0]["id"] == undated["id"]
    assert auth.get("/api/tasks?page_size=1&page=3").json()["items"] == []
    assert auth.get("/api/tasks?due_from=2026-10-26&due_through=2026-10-25").status_code == 422


def test_completion_reopen_and_trash_preserve_current_web_rules(auth):
    task = create_task(auth, create_list(auth)["id"], due_date=date(2000, 1, 1).isoformat())
    completed = send(
        auth, "PUT", f"/tasks/{task['id']}", {**payload(task), "status": "COMPLETED"}
    ).json()
    assert completed["completed_at"] and completed["id"] == task["id"]
    reopened = send(
        auth, "PUT", f"/tasks/{task['id']}", {**payload(completed), "status": "TODO"}
    ).json()
    assert reopened["completed_at"] is None
    assert (
        send(
            auth,
            "DELETE",
            f"/tasks/{task['id']}",
            {"confirmed": False, "version": reopened["version"]},
        ).status_code
        == 422
    )
    assert (
        send(
            auth,
            "DELETE",
            f"/tasks/{task['id']}",
            {"confirmed": True, "version": reopened["version"]},
        ).status_code
        == 200
    )
    assert auth.get("/api/tasks").json()["total"] == 0
    trash = auth.get("/api/tasks?trashed=true").json()
    assert trash["total"] == 1 and trash["items"][0]["purge_after"]
    assert (
        send(
            auth, "DELETE", f"/lists/{task['list_id']}", {"confirmed": True, "version": 1}
        ).status_code
        == 409
    )


def test_imported_tasks_use_factory(auth, monkeypatch):
    task_list = create_list(auth)
    create_task(auth, task_list["id"], priority="HIGH")
    snapshot = auth.get("/api/export").json()
    batch = send(auth, "POST", "/import/preview", snapshot).json()
    calls = []
    original = TaskFactory.create

    def record(self, account_id, data):
        task = original(self, account_id, data)
        calls.append(task.id)
        return task

    monkeypatch.setattr(TaskFactory, "create", record)
    assert send(auth, "POST", f"/import/{batch['id']}/apply").status_code == 200
    assert len(calls) == 1
    assert auth.get("/api/tasks").json()["total"] == 2


def test_recurrence_uses_factory_and_remains_idempotent(auth, store, monkeypatch):
    source = create_task(auth, create_list(auth)["id"], status="COMPLETED", priority="HIGH")
    result = send(
        auth,
        "PUT",
        f"/tasks/{source['id']}/recurrence",
        {"frequency": "daily", "start": "2026-10-25", "end_date": "2026-10-25"},
    )
    assert result.status_code == 200
    calls = []
    original = TaskFactory.recurring

    def record(self, task, rule_id, occurrence):
        created = original(self, task, rule_id, occurrence)
        calls.append(created.id)
        return created

    monkeypatch.setattr(TaskFactory, "recurring", record)
    for _ in range(2):
        with store.begin() as db:
            run_due(db, datetime(2026, 10, 25, 12, tzinfo=UTC))
    assert len(calls) == 1
    items = auth.get("/api/tasks").json()["items"]
    instance = next(row for row in items if row["id"] == calls[0])
    assert instance["status"] == "TODO" and instance["priority"] == "HIGH"
    assert instance["completed_at"] is None and len(items) == 2
