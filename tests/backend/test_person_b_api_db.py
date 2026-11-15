"""Person B Sprint 2 API/service and database tests for the account and admin endpoints."""

from conftest import create_list, create_task, register, send
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from tasktrack.models import Account, LoginSession, Task, TaskList

PASSWORD = "safe password 123"
FAKE_ID = "00000000-0000-4000-8000-000000000000"


def make_admin(client, store, email="admin@example.com"):
    register(client, store, email=email, password=PASSWORD)
    with store.begin() as db:
        db.scalar(select(Account).where(Account.email == email)).role = "ADMIN"
    return client


def create(client, email, role="USER", password=PASSWORD):
    return send(
        client, "POST", "/admin/accounts", {"email": email, "password": password, "role": role}
    )


# ----- API/service: correct responses -----


def test_account_responses_have_exact_shape_and_never_include_secrets(client, store):
    make_admin(client, store)
    created = create(client, "Shape@Example.com")
    assert created.status_code == 201
    expected = {"id", "email", "role", "active", "timezone", "email_reminders"}
    for body in [
        created.json(),
        client.get("/api/me").json(),
        *client.get("/api/admin/accounts").json(),
    ]:
        assert set(body) == expected
    text = created.text + client.get("/api/admin/accounts").text
    assert "password" not in text and "argon2" not in text


def test_admin_status_and_delete_return_documented_codes(client, store):
    make_admin(client, store)
    user = create(client, "user@example.com").json()
    status = send(client, "PATCH", f"/admin/accounts/{user['id']}/status", {"active": False})
    assert status.status_code == 200 and status.json()["active"] is False
    deleted = send(client, "DELETE", f"/admin/accounts/{user['id']}", {"confirmed": True})
    assert deleted.status_code == 204 and deleted.content == b""


# ----- API/service: error handling -----


def test_admin_errors_for_missing_malformed_and_duplicate_accounts(client, store):
    make_admin(client, store)
    for bad in [FAKE_ID, "not-a-uuid"]:
        assert (
            send(client, "PATCH", f"/admin/accounts/{bad}/status", {"active": False}).status_code
            == 404
        )
        assert (
            send(client, "DELETE", f"/admin/accounts/{bad}", {"confirmed": True}).status_code == 404
        )
    create(client, "dup@example.com")
    assert create(client, "DUP@example.com").status_code == 409


def test_admin_validation_errors(client, store):
    make_admin(client, store)
    user = create(client, "user@example.com").json()
    assert create(client, "bad@example.com", role="OWNER").status_code == 422
    assert create(client, "short@example.com", password="x" * 11).status_code == 422
    assert create(client, "not-an-email").status_code == 422
    path = f"/admin/accounts/{user['id']}"
    assert send(client, "DELETE", path, {"confirmed": False}).status_code == 422
    assert send(client, "DELETE", path, {}).status_code == 422
    assert send(client, "PATCH", path + "/status", {"active": "maybe"}).status_code == 422


def test_last_active_admin_is_protected_but_a_second_admin_can_be_removed(client, store):
    make_admin(client, store)
    second = create(client, "second@example.com", role="ADMIN").json()
    assert (
        send(client, "DELETE", f"/admin/accounts/{second['id']}", {"confirmed": True}).status_code
        == 204
    )
    me = client.get("/api/me").json()["id"]
    assert send(client, "DELETE", f"/admin/accounts/{me}", {"confirmed": True}).status_code == 409


# ----- Database: CRUD integrity -----


def test_account_crud_round_trip_in_database(client, store):
    register(client, store)  # Create
    me = client.get("/api/me").json()  # Read through the API
    with store() as db:  # Read from the database
        row = db.get(Account, me["id"])
        assert (row.email, row.role, row.active) == ("student@example.com", "USER", True)
        assert row.verified_at is not None
    prefs = {"timezone": "America/New_York", "email_reminders": True}
    assert send(client, "PATCH", "/me", prefs).status_code == 200  # Update
    with store() as db:
        row = db.get(Account, me["id"])
        assert (row.timezone, row.email_reminders) == ("America/New_York", True)
        old_hash = row.password_hash
    change = {"current_password": PASSWORD, "new_password": "another safe pass"}
    assert send(client, "POST", "/me/password", change).status_code == 200
    with store() as db:
        assert db.get(Account, me["id"]).password_hash != old_hash
    body = {"current_password": "another safe pass", "confirmed": True}
    assert send(client, "DELETE", "/me", body).status_code == 200  # Delete
    with store() as db:
        assert db.get(Account, me["id"]) is None


def test_admin_delete_cascades_only_the_target_accounts_data(client, store):
    register(client, store, email="keep@example.com")
    create_task(client, create_list(client)["id"])
    with TestClient(client.app) as target:
        register(target, store, email="remove@example.com")
        create_task(target, create_list(target)["id"])
        target_id = target.get("/api/me").json()["id"]
    with TestClient(client.app) as admin:
        make_admin(admin, store)
        assert (
            send(admin, "DELETE", f"/admin/accounts/{target_id}", {"confirmed": True}).status_code
            == 204
        )
    with store() as db:
        assert db.get(Account, target_id) is None
        for model in (TaskList, Task, LoginSession):
            assert (
                db.scalar(
                    select(func.count()).select_from(model).where(model.account_id == target_id)
                )
                == 0
            )
        keep = db.scalar(select(Account).where(Account.email == "keep@example.com"))
        assert (
            db.scalar(select(func.count()).select_from(Task).where(Task.account_id == keep.id)) == 1
        )


def test_email_uniqueness_is_enforced_by_the_database(store):
    import pytest
    from sqlalchemy.exc import IntegrityError
    from tasktrack.factories import AccountFactory

    with store.begin() as db:
        db.add(AccountFactory().create("same@example.com", "hash-1"))
    with pytest.raises(IntegrityError), store.begin() as db:
        db.add(AccountFactory().create("same@example.com", "hash-2"))
