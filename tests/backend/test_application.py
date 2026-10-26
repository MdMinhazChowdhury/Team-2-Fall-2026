from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import create_list, create_task, mail_token, payload, register, send
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from tasktrack import main
from tasktrack.config import settings
from tasktrack.db import now
from tasktrack.models import (
    Account,
    Activity,
    ChecklistItem,
    LoginSession,
    Notification,
    Outbox,
    Reminder,
    Task,
    Token,
)
from tasktrack.security import digest


def test_auth_verification_single_use_and_hashed_secrets(client, store):
    credentials = {"email": "Student@Example.com", "password": "  safe password 123  "}
    assert send(client, "POST", "/auth/register", credentials).status_code == 202
    assert send(client, "POST", "/auth/login", credentials).status_code == 403
    token = mail_token(store, "verify")
    with store() as db:
        account = db.scalar(select(Account))
        assert account.email == "student@example.com"
        assert account.password_hash.startswith("$argon2id$")
        assert db.scalar(select(Token)).secret_hash == digest(token)
        assert token not in db.scalar(select(Outbox)).encrypted_payload
    assert send(client, "POST", "/auth/verify", {"token": token}).status_code == 200
    assert send(client, "POST", "/auth/verify", {"token": token}).status_code == 400
    assert send(client, "POST", "/auth/login", credentials).status_code == 200
    assert client.get("/api/me").status_code == 200
    with store() as db:
        assert db.scalar(select(LoginSession)).secret_hash == digest(
            client.cookies["tasktrack_session"]
        )
    assert "HttpOnly" in client.cookies.get("tasktrack_session", "") or client.cookies.get(
        "tasktrack_session"
    )
    assert send(client, "POST", "/auth/logout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_recovery_revokes_sessions_and_is_single_use(auth, store):
    old_cookie = auth.cookies["tasktrack_session"]
    assert send(auth, "POST", "/auth/forgot", {"email": "student@example.com"}).status_code == 202
    token = mail_token(store, "reset")
    data = {"token": token, "password": "replacement secret 123"}
    assert send(auth, "POST", "/auth/reset", data).status_code == 200
    assert send(auth, "POST", "/auth/reset", data).status_code == 400
    auth.cookies.set("tasktrack_session", old_cookie)
    assert auth.get("/api/me").status_code == 401
    assert (
        send(
            auth,
            "POST",
            "/auth/login",
            {"email": "student@example.com", "password": "replacement secret 123"},
        ).status_code
        == 200
    )


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {"name": "x" * 101}])
def test_list_validation(auth, body):
    assert send(auth, "POST", "/lists", body).status_code == 422
    assert auth.get("/api/lists").json() == []


def test_list_confirmation_versions_and_nonempty_policy(auth):
    item = create_list(auth, "x" * 100)
    renamed = send(auth, "PATCH", "/lists/" + item["id"], {"name": "Renamed", "version": 1})
    assert renamed.status_code == 200
    assert (
        send(auth, "PATCH", "/lists/" + item["id"], {"name": "Stale", "version": 1}).status_code
        == 409
    )
    assert (
        send(auth, "DELETE", "/lists/" + item["id"], {"confirmed": False, "version": 2}).status_code
        == 422
    )
    create_task(auth, item["id"])
    assert (
        send(auth, "DELETE", "/lists/" + item["id"], {"confirmed": True, "version": 2}).status_code
        == 409
    )
    empty = create_list(auth, "Empty")
    assert (
        send(auth, "DELETE", "/lists/" + empty["id"], {"confirmed": True, "version": 1}).status_code
        == 200
    )


@pytest.mark.parametrize(
    "change",
    [
        {"title": ""},
        {"title": " "},
        {"title": "x" * 201},
        {"description": "x" * 5001},
        {"priority": "URGENT"},
        {"status": "INVALID"},
        {"due_date": "2026-02-29"},
    ],
)
def test_task_validation(auth, change):
    item = create_list(auth)
    assert (
        send(
            auth, "POST", "/tasks", {"list_id": item["id"], "title": "Valid", **change}
        ).status_code
        == 422
    )
    assert auth.get("/api/tasks").json()["total"] == 0


def test_create_edit_move_status_priority_checklist_and_conflict(auth):
    first, second = create_list(auth), create_list(auth, "Home")
    task = create_task(
        auth,
        first["id"],
        title="x" * 200,
        description="x" * 5000,
        due_date="2024-02-29",
        checklist=[{"text": "First"}, {"text": "Second"}],
    )
    assert task["priority"] == "MEDIUM" and task["status"] == "TODO"
    for status, priority in zip(
        ["IN_PROGRESS", "COMPLETED", "TODO"], ["LOW", "HIGH", "MEDIUM"], strict=True
    ):
        body = {
            **payload(task),
            "status": status,
            "priority": priority,
            "list_id": second["id"],
            "checklist": [
                {"text": "Second", "completed": True},
                {"text": "Edited first", "completed": False},
            ],
        }
        result = send(auth, "PUT", "/tasks/" + task["id"], body)
        assert result.status_code == 200, result.text
        assert send(auth, "PUT", "/tasks/" + task["id"], body).status_code == 409
        task = result.json()
        assert task["checklist"][0]["text"] == "Second" and task["priority"] == priority
    assert task["completed_at"] is None
    history = auth.get(f"/api/tasks/{task['id']}/activity").json()
    assert {"created", "completed", "reopened"} <= {item["event"] for item in history}


def test_trash_restoration_deadline_and_permanent_delete(auth, store):
    task = create_task(auth, create_list(auth)["id"])
    assert (
        send(auth, "DELETE", f"/tasks/{task['id']}", {"confirmed": False, "version": 1}).status_code
        == 422
    )
    assert (
        send(auth, "DELETE", f"/tasks/{task['id']}", {"confirmed": True, "version": 1}).status_code
        == 200
    )
    assert auth.get("/api/tasks").json()["total"] == 0
    deleted = auth.get("/api/tasks?trashed=true").json()["items"][0]
    assert datetime.fromisoformat(deleted["purge_after"]) - datetime.fromisoformat(
        deleted["deleted_at"]
    ) >= timedelta(days=30)
    assert (
        send(
            auth, "POST", f"/tasks/{task['id']}/restore", {"confirmed": True, "version": 2}
        ).status_code
        == 200
    )
    assert (
        send(auth, "DELETE", f"/tasks/{task['id']}", {"confirmed": True, "version": 3}).status_code
        == 200
    )
    with store.begin() as db:
        db.get(Task, task["id"]).purge_after = now() - timedelta(seconds=1)
    assert (
        send(
            auth, "POST", f"/tasks/{task['id']}/restore", {"confirmed": True, "version": 4}
        ).status_code
        == 409
    )
    assert (
        send(
            auth, "DELETE", f"/tasks/{task['id']}/permanent", {"confirmed": True, "version": 4}
        ).status_code
        == 200
    )
    assert auth.get(f"/api/tasks/{task['id']}").status_code == 404


def test_account_isolation_every_resource(auth, store):
    item = create_list(auth)
    tag = send(auth, "POST", "/tags", {"name": "Private"}).json()
    task = create_task(auth, item["id"], tag_ids=[tag["id"]])
    data = auth.get("/api/export").json()
    batch = send(auth, "POST", "/import/preview", data).json()
    with TestClient(main.app) as other:
        register(other, store, "other@example.com")
        for path in [
            f"/tasks/{task['id']}",
            f"/tasks/{task['id']}/activity",
            f"/tasks/{task['id']}/schedule",
        ]:
            assert other.get("/api" + path).status_code == 404
        assert (
            send(
                other, "PATCH", f"/lists/{item['id']}", {"name": "Hacked", "version": 1}
            ).status_code
            == 404
        )
        assert send(other, "PUT", f"/tasks/{task['id']}", payload(task)).status_code == 404
        assert (
            send(
                other, "DELETE", f"/tasks/{task['id']}", {"confirmed": True, "version": 1}
            ).status_code
            == 404
        )
        assert send(other, "PATCH", f"/tags/{tag['id']}", {"name": "Hacked"}).status_code == 404
        assert send(other, "POST", f"/import/{batch['id']}/apply").status_code == 404
        assert other.get("/api/tasks?list_id=" + item["id"]).status_code == 404
        assert other.get("/api/tasks?tag_id=" + tag["id"]).status_code == 404
        assert other.get("/api/export").json()["tasks"] == []
        assert other.get("/api/notifications").json() == []


def test_csrf_origin_errors_rate_limit_and_headers(client, store, monkeypatch):
    data = {"email": "student@example.com", "password": "safe password 123"}
    assert client.post("/api/auth/register", json=data).status_code == 403
    token = client.get("/api/auth/csrf").json()["token"]
    assert (
        client.post(
            "/api/auth/register",
            json=data,
            headers={"Origin": "https://attacker.example", "X-CSRF-Token": token},
        ).status_code
        == 403
    )
    monkeypatch.setattr(settings(), "rate_limit", 1)
    assert send(client, "POST", "/auth/register", data).status_code == 429
    response = client.get("/api/health/live")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"
    response = send(
        client,
        "POST",
        "/auth/login",
        {"email": "not-an-email", "password": "never-return-this-secret"},
    )
    assert "never-return-this-secret" not in response.text


def test_dashboard_filters_pagination_reports(auth, monkeypatch):
    import tasktrack.task_api as module

    clock = datetime(2026, 10, 25, 12, tzinfo=UTC)
    monkeypatch.setattr(module, "now", lambda: clock)
    item = create_list(auth)
    tag = send(auth, "POST", "/tags", {"name": "School"}).json()
    create_task(
        auth, item["id"], title="Today", due_date="2026-10-25", priority="HIGH", tag_ids=[tag["id"]]
    )
    create_task(auth, item["id"], title="Overdue", due_date="2026-10-24")
    create_task(auth, item["id"], title="Upcoming", due_date="2026-10-26")
    create_task(auth, item["id"], title="Undated")
    create_task(auth, item["id"], title="Finished", due_date="2026-10-24", status="COMPLETED")
    data = auth.get("/api/dashboard").json()
    assert (data["today"], data["overdue"], data["upcoming"]) == (1, 1, 1)
    assert data["status"] == {"TODO": 4, "IN_PROGRESS": 0, "COMPLETED": 1}
    result = auth.get(
        f"/api/tasks?q=Tod&priority=HIGH&status=TODO&tag_id={tag['id']}&due=today&list_id={item['id']}"
    ).json()
    assert result["total"] == 1 and result["items"][0]["title"] == "Today"
    assert auth.get("/api/tasks?due_from=2026-10-25&due_through=2026-10-25").json()["total"] == 1
    assert auth.get("/api/tasks?due=undated").json()["total"] == 1
    assert auth.get("/api/tasks?page_size=2&page=2&sort=priority").json()["total"] == 5
    assert len(auth.get("/api/tasks?page_size=2&page=2").json()["items"]) == 2
    assert auth.get("/api/tasks?page=0").status_code == 422
    assert auth.get("/api/tasks?due_from=2026-10-26&due_through=2026-10-25").status_code == 422
    today = now().date().isoformat()
    report = auth.get(f"/api/reports?start={today}&end={today}").json()
    assert sum(report["completions"].values()) == 1


def test_bulk_rollback_and_tag_management(auth):
    item = create_list(auth)
    first, second = create_task(auth, item["id"]), create_task(auth, item["id"], title="Second")
    bad = {
        "items": [{"id": first["id"], "version": 1}, {"id": second["id"], "version": 2}],
        "action": "complete",
    }
    assert send(auth, "POST", "/bulk", bad).status_code == 409
    assert auth.get(f"/api/tasks/{first['id']}").json()["status"] == "TODO"
    bad["items"][1]["version"] = 1
    assert send(auth, "POST", "/bulk", bad).json()["changed"] == 2
    tag = send(auth, "POST", "/tags", {"name": "School"}).json()
    assert send(auth, "POST", "/tags", {"name": "SCHOOL"}).status_code == 409
    assert send(auth, "PATCH", f"/tags/{tag['id']}", {"name": "Renamed"}).status_code == 200
    assert send(auth, "DELETE", f"/tags/{tag['id']}").status_code == 200


def test_export_import_preview_validation_apply_once_and_rollback(auth, monkeypatch):
    import tasktrack.extras_api as module

    item = create_list(auth)
    create_task(auth, item["id"], checklist=[{"text": "Preserved", "completed": True}])
    exported = auth.get("/api/export").json()
    invalid = {**exported, "version": 2}
    assert send(auth, "POST", "/import/preview", invalid).status_code == 422
    preview = send(auth, "POST", "/import/preview", exported).json()
    assert auth.get("/api/tasks").json()["total"] == 1
    original = module.save_task

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("SIMULATED_DATABASE_INTERNAL_SECRET")

    monkeypatch.setattr(module, "save_task", fail)
    result = send(auth, "POST", f"/import/{preview['id']}/apply")
    assert result.status_code == 503 and "SIMULATED_DATABASE_INTERNAL_SECRET" not in result.text
    assert len(auth.get("/api/lists").json()) == 1
    assert auth.get("/api/tasks").json()["total"] == 1
    monkeypatch.setattr(module, "save_task", original)
    assert send(auth, "POST", f"/import/{preview['id']}/apply").status_code == 200
    assert send(auth, "POST", f"/import/{preview['id']}/apply").status_code == 409
    assert auth.get("/api/tasks").json()["total"] == 2
    assert all(item["checklist"][0]["completed"] for item in auth.get("/api/tasks").json()["items"])


def test_preferences_password_sessions_and_account_delete(auth, store):
    assert (
        send(
            auth, "PATCH", "/me", {"timezone": "invalid/zone", "email_reminders": True}
        ).status_code
        == 422
    )
    assert (
        send(
            auth, "PATCH", "/me", {"timezone": "America/New_York", "email_reminders": True}
        ).status_code
        == 200
    )
    old_cookie = auth.cookies["tasktrack_session"]
    assert (
        send(
            auth,
            "POST",
            "/me/password",
            {"current_password": "safe password 123", "new_password": "a new safe password 123"},
        ).status_code
        == 200
    )
    assert auth.cookies["tasktrack_session"] != old_cookie
    assert len(auth.get("/api/me/sessions").json()) == 1
    item = create_list(auth)
    task = create_task(auth, item["id"], checklist=[{"text": "Delete me"}])
    assert task["checklist"]
    assert (
        send(auth, "DELETE", "/me", {"current_password": "wrong", "confirmed": True}).status_code
        == 400
    )
    assert (
        send(
            auth,
            "DELETE",
            "/me",
            {"current_password": "a new safe password 123", "confirmed": True},
        ).status_code
        == 200
    )
    with store() as db:
        for model in (Account, Task, ChecklistItem, LoginSession, Activity, Outbox):
            assert db.scalar(select(func.count()).select_from(model)) == 0
    assert auth.get("/api/me").status_code == 401


def test_recurring_jobs_reminder_deduplication_and_restart(auth, store):
    from tasktrack.jobs import run_due

    item = create_list(auth)
    task = create_task(auth, item["id"], checklist=[{"text": "Copy checklist"}])
    assert (
        send(
            auth,
            "PUT",
            f"/tasks/{task['id']}/recurrence",
            {"frequency": "monthly", "start": "2026-01-31", "end_date": "2026-03-31"},
        ).status_code
        == 200
    )
    with store.begin() as db:
        run_due(db, datetime(2026, 3, 31, 23, tzinfo=UTC))
    with store.begin() as db:
        run_due(db, datetime(2026, 3, 31, 23, tzinfo=UTC))
        assert db.scalar(select(func.count()).select_from(Task)) == 4
        dates = list(
            db.scalars(
                select(Task.due_date).where(Task.recurrence_id.is_not(None)).order_by(Task.due_date)
            )
        )
        assert dates == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
        db.add(
            Reminder(
                account_id=db.get(Task, task["id"]).account_id,
                task_id=task["id"],
                scheduled_at=now() - timedelta(seconds=1),
            )
        )
    with store.begin() as db:
        run_due(db)
    with store.begin() as db:
        run_due(db)
        assert db.scalar(select(func.count()).select_from(Notification)) == 1
    notification = auth.get("/api/notifications").json()[0]
    assert send(auth, "POST", f"/notifications/{notification['id']}/read").status_code == 200
    assert auth.get("/api/notifications").json()[0]["read_at"]


def test_mail_retry_bounded_and_encrypted(client, store, monkeypatch):
    from tasktrack import jobs

    send(
        client,
        "POST",
        "/auth/register",
        {"email": "student@example.com", "password": "safe password 123"},
    )

    def unavailable(*args):
        raise OSError("secret SMTP configuration")

    monkeypatch.setattr(jobs, "send_mail", unavailable)
    for attempt in range(5):
        with store.begin() as db:
            jobs.deliver_outbox(db, now() + timedelta(days=attempt + 1))
    with store() as db:
        mail = db.scalar(select(Outbox))
        assert mail.status == "failed" and mail.attempts == 5
        assert mail.error_code == "smtp_delivery_failed"
        assert "secret" not in mail.encrypted_payload
