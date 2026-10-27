"""Person B account factory and authorization tests without a database."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from tasktrack.account_services import AccountService, account_data
from tasktrack.factories import AccountFactory
from tasktrack.schemas import AdminAccountCreate


def test_account_factory_normalizes_defaults_and_generates_unique_ids(monkeypatch):
    clock = datetime(2026, 10, 26, 12, tzinfo=UTC)
    monkeypatch.setattr("tasktrack.factories.now", lambda: clock)
    first = AccountFactory().create("  Student@Example.COM ", "argon-hash")
    second = AccountFactory().create("student@example.com", "argon-hash")
    assert first.id != second.id
    assert str(UUID(first.id)) == first.id
    assert first.email == "student@example.com"
    assert first.role == "USER" and first.active is True
    assert first.created_at == clock and first.verified_at is None


def test_account_factory_accepts_admin_case_insensitively():
    account = AccountFactory().create(
        "admin@example.com",
        "argon-hash",
        "admin",
        verified_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    assert account.role == "ADMIN"
    assert account.verified_at is not None


@pytest.mark.parametrize(
    "email,password_hash,role",
    [
        ("", "hash", "USER"),
        ("person@example.com", "", "USER"),
        ("person@example.com", "hash", ""),
        ("person@example.com", "hash", "OWNER"),
    ],
)
def test_account_factory_rejects_invalid_inputs(email, password_hash, role):
    with pytest.raises(ValueError):
        AccountFactory().create(email, password_hash, role)


@pytest.mark.parametrize("role", ["USER", "ADMIN"])
def test_admin_schema_accepts_supported_roles(role):
    data = AdminAccountCreate(
        email="person@example.com",
        password="safe password 123",
        role=role,
    )
    assert data.role == role


def test_admin_schema_rejects_unknown_roles_and_short_passwords():
    with pytest.raises(ValidationError):
        AdminAccountCreate(
            email="person@example.com",
            password="safe password 123",
            role="OWNER",
        )
    with pytest.raises(ValidationError):
        AdminAccountCreate(email="person@example.com", password="short")


def test_admin_authorization_requires_active_admin():
    admin = AccountFactory().create("admin@example.com", "hash", "ADMIN")
    AccountService.require_admin(admin)
    for role, active in [("USER", True), ("ADMIN", False)]:
        account = AccountFactory().create("person@example.com", "hash", role)
        account.active = active
        with pytest.raises(HTTPException) as failure:
            AccountService.require_admin(account)
        assert failure.value.status_code == 403


def test_account_response_contains_only_expected_metadata():
    account = AccountFactory().create("person@example.com", "hash", "USER")
    account.timezone = "UTC"
    account.email_reminders = False
    assert account_data(account) == {
        "id": account.id,
        "email": "person@example.com",
        "role": "USER",
        "active": True,
        "timezone": "UTC",
        "email_reminders": False,
    }
