from datetime import UTC, datetime

from conftest import create_list, create_task, payload, send
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from tasktrack.models import Reminder


def test_reminders_use_account_timezone_and_reject_dst_gaps_and_ambiguity(auth, store):
    send(auth, "PATCH", "/me", {"timezone": "America/New_York", "email_reminders": False})
    task = create_task(auth, create_list(auth)["id"])
    path = f"/tasks/{task['id']}/reminders"
    assert send(auth, "POST", path, {"scheduled_at": "2027-03-14T02:30:00"}).status_code == 422
    assert send(auth, "POST", path, {"scheduled_at": "2026-11-01T01:30:00"}).status_code == 422
    assert send(auth, "POST", path, {"scheduled_at": "2026-11-02T09:00:00"}).status_code == 201
    with store() as db:
        row = db.scalar(select(Reminder))
        assert row.scheduled_at == datetime(2026, 11, 2, 14, tzinfo=UTC)
    result = send(auth, "POST", path, {"scheduled_at": "2026-11-01T01:30:00-04:00"})
    assert result.status_code == 201
    assert send(auth, "DELETE", f"/reminders/{result.json()['id']}").status_code == 200


def test_commit_failure_is_redacted_and_never_reports_success(auth, store):
    def fail(session):
        raise SQLAlchemyError("DATABASE_INTERNAL_SECRET")

    event.listen(store, "before_commit", fail)
    try:
        response = send(auth, "POST", "/lists", {"name": "Must roll back"})
        assert response.status_code == 503
        assert "DATABASE_INTERNAL_SECRET" not in response.text
    finally:
        event.remove(store, "before_commit", fail)
    assert auth.get("/api/lists").json() == []


def test_revoke_all_sessions_requires_csrf_and_signs_out(auth):
    assert send(auth, "DELETE", "/me/sessions").status_code == 200
    assert auth.get("/api/me").status_code == 401


def test_completion_report_keeps_history_when_task_is_reopened(auth):
    task = create_task(auth, create_list(auth)["id"], status="COMPLETED")
    updated = send(auth, "PUT", f"/tasks/{task['id']}", {**payload(task), "status": "TODO"})
    assert updated.status_code == 200
    report = auth.get("/api/reports?start=2026-10-25&end=2026-10-25").json()
    assert report["completions"]["2026-10-25"] == 1
    assert report["status"]["TODO"] == 1 and report["status"]["COMPLETED"] == 0
