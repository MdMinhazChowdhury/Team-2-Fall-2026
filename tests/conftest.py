import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

TEST_URL = os.environ.get("TASKTRACK_TEST_DATABASE_URL")
if not TEST_URL or not TEST_URL.startswith("postgresql+psycopg://"):
    raise RuntimeError(
        "Set TASKTRACK_TEST_DATABASE_URL to an isolated PostgreSQL database; tests never fall back to SQLite"
    )
os.environ["TASKTRACK_DATABASE_URL"] = TEST_URL
os.environ["TASKTRACK_ENV"] = "test"
os.environ["TASKTRACK_TEST_NOW"] = "2026-10-25T12:00:00Z"

from tasktrack import db as database_module  # noqa: E402
from tasktrack import main  # noqa: E402
from tasktrack.adapters import cipher  # noqa: E402
from tasktrack.config import settings  # noqa: E402
from tasktrack.db import Base  # noqa: E402
from tasktrack.models import Outbox  # noqa: E402


def send(client, method, path, data=None):
    token = client.get("/api/auth/csrf").json()["token"]
    return client.request(
        method,
        "/api" + path,
        json=data,
        headers={"Origin": settings().public_origin, "X-CSRF-Token": token},
    )


@pytest.fixture
def store(monkeypatch):
    engine = create_engine(TEST_URL)
    schema = "test_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    factory = sessionmaker(scoped, expire_on_commit=False)
    monkeypatch.setattr(database_module, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(settings(), "rate_limit", 500)
    yield factory
    scoped.dispose()
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


@pytest.fixture
def client(store):
    with TestClient(main.app) as client:
        yield client


def mail_token(store, purpose):
    with store() as db:
        for mail in reversed(list(db.scalars(select(Outbox)))):
            body = json.loads(cipher().decrypt(mail.encrypted_payload.encode()))["body"]
            if f"#{purpose}=" in body:
                return body.split(f"#{purpose}=")[1].strip()
    raise AssertionError("No verification/recovery email queued")


def register(client, store, email="student@example.com", password="safe password 123"):
    assert (
        send(client, "POST", "/auth/register", {"email": email, "password": password}).status_code
        == 202
    )
    token = mail_token(store, "verify")
    assert send(client, "POST", "/auth/verify", {"token": token}).status_code == 200
    assert (
        send(client, "POST", "/auth/login", {"email": email, "password": password}).status_code
        == 200
    )
    return client


@pytest.fixture
def auth(client, store):
    return register(client, store)


def create_list(client, name="School"):
    response = send(client, "POST", "/lists", {"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def create_task(client, list_id, **values):
    response = send(client, "POST", "/tasks", {"list_id": list_id, "title": "Assignment", **values})
    assert response.status_code == 201, response.text
    return response.json()


def payload(task):
    return {
        key: value
        for key, value in task.items()
        if key
        in {
            "list_id",
            "title",
            "description",
            "due_date",
            "priority",
            "status",
            "checklist",
            "tag_ids",
            "version",
        }
    }
