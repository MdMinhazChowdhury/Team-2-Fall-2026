"""PostgreSQL integration coverage for Person B account administration."""

from conftest import register, send
from fastapi.testclient import TestClient
from sqlalchemy import select
from tasktrack.models import Account, LoginSession

PASSWORD = "safe password 123"


def make_admin(client, store, email="admin@example.com"):
    register(client, store, email=email, password=PASSWORD)
    with store.begin() as db:
        account = db.scalar(select(Account).where(Account.email == email))
        account.role = "ADMIN"
    return client


def test_admin_can_create_and_list_verified_accounts(client, store):
    make_admin(client, store)
    response = send(
        client,
        "POST",
        "/admin/accounts",
        {
            "email": "Manager@Example.com",
            "password": "another safe password",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["email"] == "manager@example.com"
    assert created["role"] == "ADMIN" and created["active"] is True
    listed = send(client, "GET", "/admin/accounts")
    assert listed.status_code == 200
    assert [row["email"] for row in listed.json()] == [
        "admin@example.com",
        "manager@example.com",
    ]
    with store() as db:
        account = db.get(Account, created["id"])
        assert account.verified_at is not None
        assert account.password_hash != "another safe password"


def test_regular_user_cannot_use_admin_routes(client, store):
    register(client, store)
    assert send(client, "GET", "/admin/accounts").status_code == 403
    assert (
        send(
            client,
            "POST",
            "/admin/accounts",
            {
                "email": "other@example.com",
                "password": "another safe password",
                "role": "USER",
            },
        ).status_code
        == 403
    )


def test_disable_revokes_sessions_blocks_login_and_enable_restores_access(client, store):
    make_admin(client, store)
    created = send(
        client,
        "POST",
        "/admin/accounts",
        {
            "email": "person@example.com",
            "password": PASSWORD,
            "role": "USER",
        },
    ).json()
    with TestClient(client.app) as second_client:
        assert (
            send(
                second_client,
                "POST",
                "/auth/login",
                {
                    "email": "person@example.com",
                    "password": PASSWORD,
                },
            ).status_code
            == 200
        )
        with store() as db:
            assert db.scalar(select(LoginSession).where(LoginSession.account_id == created["id"]))
        disabled = send(
            client, "PATCH", "/admin/accounts/" + created["id"] + "/status", {"active": False}
        )
        assert disabled.status_code == 200 and disabled.json()["active"] is False
        assert second_client.get("/api/me").status_code == 401
        assert (
            send(
                second_client,
                "POST",
                "/auth/login",
                {
                    "email": "person@example.com",
                    "password": PASSWORD,
                },
            ).status_code
            == 403
        )
        enabled = send(
            client, "PATCH", "/admin/accounts/" + created["id"] + "/status", {"active": True}
        )
        assert enabled.status_code == 200 and enabled.json()["active"] is True
        assert (
            send(
                second_client,
                "POST",
                "/auth/login",
                {
                    "email": "person@example.com",
                    "password": PASSWORD,
                },
            ).status_code
            == 200
        )


def test_admin_cannot_disable_or_delete_self(client, store):
    make_admin(client, store)
    me = client.get("/api/me").json()
    assert (
        send(
            client, "PATCH", "/admin/accounts/" + me["id"] + "/status", {"active": False}
        ).status_code
        == 409
    )
    assert (
        send(client, "DELETE", "/admin/accounts/" + me["id"], {"confirmed": True}).status_code
        == 409
    )


def test_admin_can_delete_another_account(client, store):
    make_admin(client, store)
    created = send(
        client,
        "POST",
        "/admin/accounts",
        {
            "email": "delete@example.com",
            "password": PASSWORD,
            "role": "USER",
        },
    ).json()
    response = send(client, "DELETE", "/admin/accounts/" + created["id"], {"confirmed": True})
    assert response.status_code == 204
    with store() as db:
        assert db.get(Account, created["id"]) is None


def test_admin_validation_and_duplicate_email(client, store):
    make_admin(client, store)
    duplicate = send(
        client,
        "POST",
        "/admin/accounts",
        {
            "email": "ADMIN@example.com",
            "password": PASSWORD,
            "role": "USER",
        },
    )
    assert duplicate.status_code == 409
    invalid_role = send(
        client,
        "POST",
        "/admin/accounts",
        {
            "email": "new@example.com",
            "password": PASSWORD,
            "role": "OWNER",
        },
    )
    assert invalid_role.status_code == 422
    missing = send(
        client,
        "PATCH",
        "/admin/accounts/not-a-uuid/status",
        {
            "active": False,
        },
    )
    assert missing.status_code == 404
