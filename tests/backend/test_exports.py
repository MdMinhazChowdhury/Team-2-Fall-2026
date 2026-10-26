from conftest import create_list, create_task, register, send
from fastapi.testclient import TestClient
from tasktrack import main
from tasktrack.jobs import run_exports


def test_durable_export_job_restart_owner_scope_and_download(auth, store):
    create_task(auth, create_list(auth)["id"], title="Durable export")
    job = send(auth, "POST", "/exports").json()
    assert job["status"] == "pending"
    assert auth.get(f"/api/exports/{job['id']}/download").status_code == 409
    with store.begin() as db:
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        run_exports(db)
    with store.begin() as db:
        run_exports(db)
    assert auth.get(f"/api/exports/{job['id']}").json()["status"] == "ready"
    assert (
        auth.get(f"/api/exports/{job['id']}/download").json()["tasks"][0]["title"]
        == "Durable export"
    )
    with TestClient(main.app) as other:
        register(other, store, "other@example.com")
        assert other.get(f"/api/exports/{job['id']}").status_code == 404
        assert other.get(f"/api/exports/{job['id']}/download").status_code == 404
