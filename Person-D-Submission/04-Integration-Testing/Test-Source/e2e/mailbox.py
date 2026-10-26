"""Read only the isolated browser-test mailbox; never use against a real database."""

import json
import os
import sys

from sqlalchemy import select

url = os.environ.get("TASKTRACK_E2E_DATABASE_URL", "")
if "/tasktrack_e2e" not in url:
    raise RuntimeError("The mailbox helper requires the separate tasktrack_e2e database")
os.environ["TASKTRACK_DATABASE_URL"] = url
os.environ["TASKTRACK_ENV"] = "test"
os.environ["TASKTRACK_TEST_NOW"] = "2026-10-25T12:00:00Z"

from tasktrack.adapters import cipher  # noqa: E402
from tasktrack.db import SessionLocal  # noqa: E402
from tasktrack.models import Account, Outbox, Task  # noqa: E402

if sys.argv[1] == "--restart-state":
    with SessionLocal() as session:
        account = session.scalar(
            select(Account)
            .join(Task, Task.account_id == Account.id)
            .where(Task.title == "Finish edited assignment", Task.deleted_at.is_(None))
            .limit(1)
        )
        if account is None:
            raise RuntimeError("No saved workflow available for restart verification")
        print(json.dumps({"email": account.email, "title": "Finish edited assignment"}))
    sys.exit(0)

if sys.argv[1] == "--exports":
    from tasktrack.jobs import run_exports

    with SessionLocal.begin() as session:
        session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        run_exports(session)
    sys.exit(0)

with SessionLocal() as db:
    account = db.scalar(select(Account).where(Account.email == sys.argv[1]))
    if not account:
        raise RuntimeError("Test account missing")
    for mail in db.scalars(select(Outbox).where(Outbox.account_id == account.id)):
        body = json.loads(cipher().decrypt(mail.encrypted_payload.encode()))["body"]
        if "#verify=" in body:
            print(body.split("#verify=")[1].strip())
            break
