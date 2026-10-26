"""NFR5 workload: 10 concurrent accounts, 500 stored tasks each, real PostgreSQL."""

import json
import platform
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from conftest import payload, send
from fastapi.testclient import TestClient
from sqlalchemy import insert
from tasktrack import main
from tasktrack.db import now
from tasktrack.models import Account, Task, TaskList, uuid
from tasktrack.security import hasher


def test_ten_accounts_five_hundred_tasks_each(store):
    hashed = hasher.hash("load test password 123")
    with store.begin() as db:
        for index in range(10):
            account = Account(
                email=f"load{index}@example.com", password_hash=hashed, verified_at=now()
            )
            db.add(account)
            db.flush()
            task_list = TaskList(account_id=account.id, name="Workload")
            db.add(task_list)
            db.flush()
            db.execute(
                insert(Task),
                [
                    {
                        "id": uuid(),
                        "account_id": account.id,
                        "list_id": task_list.id,
                        "title": f"Task {number:04}",
                    }
                    for number in range(500)
                ],
            )
    barrier = threading.Barrier(10)

    def run(index):
        with TestClient(main.app) as client:
            assert (
                send(
                    client,
                    "POST",
                    "/auth/login",
                    {"email": f"load{index}@example.com", "password": "load test password 123"},
                ).status_code
                == 200
            )
            barrier.wait(timeout=30)
            durations = []
            for _ in range(5):
                start = time.perf_counter()
                result = client.get("/api/tasks?page_size=25")
                durations.append(time.perf_counter() - start)
                assert result.status_code == 200 and result.json()["total"] == 500
                task = result.json()["items"][0]
                start = time.perf_counter()
                result = send(
                    client,
                    "PUT",
                    f"/tasks/{task['id']}",
                    {**payload(task), "title": "Updated under load"},
                )
                durations.append(time.perf_counter() - start)
                assert result.status_code == 200
            return durations

    with ThreadPoolExecutor(max_workers=10) as pool:
        samples = [sample for group in pool.map(run, range(10)) for sample in group]
    p95 = sorted(samples)[int(len(samples) * 0.95) - 1]
    evidence = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "transport": "in-process ASGI TestClient (includes API and PostgreSQL; excludes network/proxy)",
        "platform": platform.platform(),
        "concurrent_accounts": 10,
        "tasks_per_account": 500,
        "requests": len(samples),
        "get_page_size": 25,
        "median_seconds": statistics.median(samples),
        "p95_seconds": p95,
        "max_seconds": max(samples),
        "target_seconds": 2,
        "passed": p95 < 2,
    }
    Path("docs/evidence").mkdir(parents=True, exist_ok=True)
    Path("docs/evidence/performance.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf8"
    )
    assert p95 < 2, evidence
