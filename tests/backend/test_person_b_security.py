"""Person B Sprint 2 security tests (NFR1-NFR3) against real PostgreSQL through the API."""

import statistics
import time
from datetime import timedelta

import pytest
from argon2 import PasswordHasher
from conftest import create_list, create_task, register, send
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from tasktrack.config import settings
from tasktrack.db import now
from tasktrack.models import Account, LoginSession, Task

PASSWORD = "safe password 123"


def make_admin(client, store, email="admin@example.com"):
    register(client, store, email=email, password=PASSWORD)
    with store.begin() as db:
        db.scalar(select(Account).where(Account.email == email)).role = "ADMIN"
    return client


def login(client, email="student@example.com", password=PASSWORD):
    return send(client, "POST", "/auth/login", {"email": email, "password": password})


# ----- NFR1: passwords and secrets are never stored in plaintext -----


def test_password_stored_as_argon2id_with_owasp_parameters(auth, store):
    with store() as db:
        stored = db.scalar(select(Account.password_hash))
    assert PASSWORD not in stored
    assert stored.startswith("$argon2id$v=19$m=65536,t=3,p=4$")  # OWASP minimums: m>=19 MiB, t>=2
    assert PasswordHasher().verify(stored, PASSWORD)


def test_session_cookie_secret_is_stored_only_as_a_hash(auth, store):
    raw = auth.cookies.get("tasktrack_session")
    assert raw and len(raw) >= 64  # 48 random bytes, URL-safe encoded
    with store() as db:
        stored = list(db.scalars(select(LoginSession.secret_hash)))
    assert stored and raw not in stored and all(len(value) == 64 for value in stored)


# ----- NFR3: sessions, cookies, CSRF and headers -----


def test_session_cookie_flags_and_security_headers(client, store):
    register(client, store)
    response = login(client)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    headers = client.get("/api/me").headers
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_new_login_replaces_attacker_supplied_session_cookie(client, store):
    register(client, store)
    first = client.cookies.get("tasktrack_session")
    login(client)
    second = client.cookies.get("tasktrack_session")
    assert first != second
    with store() as db:
        assert db.scalar(select(func.count()).select_from(LoginSession)) == 1


def test_logged_out_or_expired_session_is_rejected(auth, store):
    stolen = auth.cookies.get("tasktrack_session")
    with store.begin() as db:
        db.execute(update(LoginSession).values(expires_at=now() - timedelta(seconds=1)))
    assert auth.get("/api/me").status_code == 401
    login(auth)
    send(auth, "POST", "/auth/logout")
    auth.cookies.set("tasktrack_session", stolen)
    assert auth.get("/api/me").status_code == 401


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/api/admin/accounts", {"email": "x@example.com", "password": PASSWORD}),
        ("POST", "/api/me/password", {"current_password": PASSWORD, "new_password": "x" * 12}),
        ("DELETE", "/api/me", {"current_password": PASSWORD, "confirmed": True}),
    ],
)
def test_state_changes_without_csrf_token_are_refused(client, store, method, path, body):
    make_admin(client, store)
    assert client.request(method, path, json=body).status_code == 403
    assert (
        client.request(
            method, path, json=body, headers={"Origin": settings().public_origin}
        ).status_code
        == 403
    )


# ----- NFR2: authorization and account isolation -----


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/admin/accounts", None),
        ("POST", "/admin/accounts", {"email": "x@example.com", "password": PASSWORD}),
        ("PATCH", "/admin/accounts/{id}/status", {"active": False}),
        ("DELETE", "/admin/accounts/{id}", {"confirmed": True}),
    ],
)
def test_every_admin_route_requires_login_and_admin_role(client, store, method, path, body):
    register(client, store, email="victim@example.com")
    victim = client.get("/api/me").json()["id"]
    path = path.format(id=victim)
    send(client, "POST", "/auth/logout")
    assert send(client, method, path, body).status_code == 401  # anonymous
    register(client, store, email="regular@example.com")
    assert send(client, method, path, body).status_code == 403  # logged in, not admin
    with store() as db:
        assert db.get(Account, victim).active is True  # nothing changed


@pytest.mark.parametrize(
    "field,value",
    [("role", "ADMIN"), ("active", True), ("verified_at", "2026-01-01T00:00:00Z")],
)
def test_privilege_fields_cannot_be_mass_assigned(client, store, field, value):
    body = {"email": "sneaky@example.com", "password": PASSWORD, field: value}
    assert send(client, "POST", "/auth/register", body).status_code == 422
    register(client, store)
    prefs = {"timezone": "UTC", "email_reminders": False, field: value}
    assert send(client, "PATCH", "/me", prefs).status_code == 422
    with store() as db:
        assert db.scalar(select(func.count()).where(Account.role == "ADMIN")) == 0


def test_admin_cannot_read_users_tasks_and_users_cannot_touch_each_other(client, store):
    register(client, store, email="owner@example.com")
    task = create_task(client, create_list(client)["id"], title="Private")
    owner_session = client.get("/api/me/sessions").json()[0]["id"]
    with TestClient(client.app) as other:
        make_admin(other, store, email="boss@example.com")
        assert other.get(f"/api/tasks/{task['id']}").status_code == 404
        assert other.get("/api/tasks").json()["items"] == []
        assert send(other, "DELETE", f"/me/sessions/{owner_session}").status_code == 404
    assert client.get("/api/me").status_code == 200  # owner's session survived


@pytest.mark.parametrize(
    "email",
    ["' OR '1'='1", "admin@example.com'; DROP TABLE accounts;--", "x@example.com\x00"],
)
def test_injection_style_input_is_rejected_without_server_error(client, store, email):
    register(client, store)
    response = login(client, email=email, password="' OR '1'='1")
    assert response.status_code in {401, 422}
    with store() as db:
        assert db.scalar(select(func.count()).select_from(Account)) == 1
        assert db.scalar(select(func.count()).select_from(Task)) == 0


# ----- Brute-force protection -----


def test_login_brute_force_is_rate_limited(client, store, monkeypatch):
    register(client, store)
    monkeypatch.setattr(settings(), "rate_limit", 5)
    codes = [login(client, password=f"wrong guess {n:02d}").status_code for n in range(8)]
    assert 429 in codes and codes.index(429) <= 5


@pytest.mark.parametrize(
    "method,path,field",
    [("POST", "/me/password", "new_password"), ("DELETE", "/me", "confirmed")],
)
def test_current_password_guessing_is_rate_limited(auth, monkeypatch, method, path, field):
    monkeypatch.setattr(settings(), "rate_limit", 5)
    value = "another safe pass" if field == "new_password" else True
    codes = [
        send(
            auth, method, path, {"current_password": f"guess {n:02d} xx", field: value}
        ).status_code
        for n in range(8)
    ]
    assert 429 in codes and codes.index(429) <= 5, codes


# ----- Measured: login gives no timing hint about which emails exist -----


def test_password_hashing_cost_slows_offline_guessing(record_property):
    from tasktrack.security import hasher

    samples = []
    for _ in range(5):
        started = time.perf_counter()
        hasher.hash(PASSWORD)
        samples.append((time.perf_counter() - started) * 1000)
    cost_ms = statistics.median(samples)
    record_property("argon2id_hash_median_ms", round(cost_ms, 1))
    record_property("max_guesses_per_second_per_core", round(1000 / cost_ms, 1))
    assert cost_ms >= 20  # each guess must cost real work; fast hashes allow millions per second
    assert cost_ms < 1000  # but logins stay responsive


def test_login_timing_does_not_reveal_registered_emails(client, store, record_property):
    register(client, store)

    def median_ms(email):
        samples = []
        for _ in range(5):
            started = time.perf_counter()
            assert login(client, email=email, password="wrong password!!").status_code == 401
            samples.append((time.perf_counter() - started) * 1000)
        return statistics.median(samples)

    known, unknown = median_ms("student@example.com"), median_ms("nobody@example.com")
    record_property("login_wrong_password_median_ms", round(known, 1))
    record_property("login_unknown_email_median_ms", round(unknown, 1))
    assert 0.5 < unknown / known < 2.0, (known, unknown)
