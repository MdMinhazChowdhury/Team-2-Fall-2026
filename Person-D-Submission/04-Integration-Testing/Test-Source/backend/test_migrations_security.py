from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from alembic import command
from alembic.config import Config
from conftest import TEST_URL, create_list, create_task, payload, send
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from tasktrack import main
from tasktrack.config import Settings, settings


def test_migration_upgrade_downgrade_and_metadata_agreement(monkeypatch):
    schema = "migration_" + uuid4().hex
    engine = create_engine(TEST_URL)
    with engine.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(TEST_URL).update_query_dict({"options": "-csearch_path=" + schema})
    monkeypatch.setattr(settings(), "database_url", url.render_as_string(hide_password=False))
    config = Config("alembic.ini")
    try:
        command.upgrade(config, "head")
        assert {"accounts", "sessions", "tasks", "outbox", "recurrences"} <= set(
            inspect(engine).get_table_names(schema=schema)
        )
        command.check(config)
        command.downgrade(config, "base")
        assert inspect(engine).get_table_names(schema=schema) == ["alembic_version"]
        command.upgrade(config, "head")
    finally:
        with engine.begin() as db:
            db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_concurrent_stale_writes_have_one_winner(auth):
    task = create_task(auth, create_list(auth)["id"])
    cookies = dict(auth.cookies)

    def update(title):
        with TestClient(main.app, cookies=cookies) as client:
            return send(
                client, "PUT", f"/tasks/{task['id']}", {**payload(task), "title": title}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, ["First writer", "Second writer"])) == [200, 409]


def test_production_configuration_fails_closed_and_cookie_flags(client, store, monkeypatch):
    import pytest

    with pytest.raises(ValueError):
        Settings(_env_file=None, env="production")
    monkeypatch.setattr(settings(), "env", "production")
    with TestClient(main.app, base_url="https://testserver") as secure:
        response = secure.get("/api/auth/csrf")
        value = response.headers["set-cookie"]
        assert "Secure" in value and "HttpOnly" in value and "SameSite=lax" in value
        assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")


def test_request_size_limit_and_error_redaction(client):
    response = client.post("/api/import/preview", content="x" * (2 * 1024 * 1024 + 1))
    assert response.status_code == 413
    assert "2 MiB" in response.json()["detail"]
