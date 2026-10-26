from datetime import date, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select

from tasktrack import schemas as s
from tasktrack.db import now
from tasktrack.filters import TaskFilter
from tasktrack.models import Activity, Tag, Task, TaskList
from tasktrack.security import DB, CurrentAccount, csrf
from tasktrack.services import details, event, owned, save_task, trash, version

router = APIRouter(prefix="/api", dependencies=[Depends(csrf)])


@router.get("/lists")
def lists(account: CurrentAccount, db: DB):
    return [
        {"id": row.id, "name": row.name, "version": row.version}
        for row in db.scalars(
            select(TaskList)
            .where(TaskList.account_id == account.id)
            .order_by(TaskList.created_at, TaskList.id)
        )
    ]


@router.post("/lists", status_code=201)
def create_list(data: s.ListInput, account: CurrentAccount, db: DB):
    row = TaskList(account_id=account.id, name=data.name)
    db.add(row)
    db.flush()
    return {"id": row.id, "name": row.name, "version": row.version}


@router.patch("/lists/{list_id}")
def rename_list(list_id: str, data: s.ListUpdate, account: CurrentAccount, db: DB):
    row = owned(db, TaskList, list_id, account.id, lock=True)
    version(row, data.version)
    row.name = data.name
    row.version += 1
    return {"id": row.id, "name": row.name, "version": row.version}


@router.delete("/lists/{list_id}")
def delete_list(list_id: str, data: s.Confirmation, account: CurrentAccount, db: DB):
    row = owned(db, TaskList, list_id, account.id, lock=True)
    version(row, data.version)
    if db.scalar(select(Task.id).where(Task.list_id == row.id).limit(1)):
        raise HTTPException(
            409,
            "Move or permanently delete this list's tasks (including Trash) before deleting the list",
        )
    db.delete(row)
    return {"message": "List deleted"}


@router.get("/tasks")
def tasks(
    account: CurrentAccount,
    db: DB,
    q: str = Query(default="", max_length=200),
    list_id: str | None = None,
    status: s.Status | None = None,
    priority: s.Priority | None = None,
    tag_id: str | None = None,
    due: Literal["today", "upcoming", "overdue", "undated"] | None = None,
    due_from: date | None = None,
    due_through: date | None = None,
    sort: Literal["due_date", "priority", "created_at"] = "due_date",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    trashed: bool = False,
):
    if due_from and due_through and due_from > due_through:
        raise HTTPException(422, "Start date must not follow end date")
    if list_id:
        owned(db, TaskList, list_id, account.id)
    if tag_id:
        owned(db, Tag, tag_id, account.id)
    clock = now()
    today = clock.astimezone(ZoneInfo(account.timezone)).date()
    query = TaskFilter(
        q=q,
        list_id=list_id,
        status=status,
        priority=priority,
        tag_id=tag_id,
        due=due,
        due_from=due_from,
        due_through=due_through,
        trashed=trashed,
    ).query(account.id, today, clock)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    ordering: Any = {
        "due_date": Task.due_date.asc().nulls_last(),
        "created_at": Task.created_at.desc(),
        "priority": case((Task.priority == "HIGH", 0), (Task.priority == "MEDIUM", 1), else_=2),
    }[sort]
    rows = db.scalars(
        query.order_by(ordering, Task.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [details(db, row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/tasks", status_code=201)
def create_task(data: s.TaskInput, account: CurrentAccount, db: DB):
    return details(db, save_task(db, account.id, data))


@router.get("/tasks/{task_id}")
def get_task(task_id: str, account: CurrentAccount, db: DB):
    return details(db, owned(db, Task, task_id, account.id))


@router.put("/tasks/{task_id}")
def update_task(task_id: str, data: s.TaskUpdate, account: CurrentAccount, db: DB):
    return details(
        db, save_task(db, account.id, data, owned(db, Task, task_id, account.id, lock=True))
    )


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, data: s.Confirmation, account: CurrentAccount, db: DB):
    row = owned(db, Task, task_id, account.id, lock=True)
    version(row, data.version)
    trash(db, row)
    return {"message": "Moved to Trash for 30 days"}


@router.post("/tasks/{task_id}/restore")
def restore_task(task_id: str, data: s.Confirmation, account: CurrentAccount, db: DB):
    row = owned(db, Task, task_id, account.id, lock=True)
    version(row, data.version)
    if not row.deleted_at or row.purge_after <= now():
        raise HTTPException(409, "This task is not recoverable")
    row.deleted_at = row.purge_after = None
    row.version += 1
    event(db, row, "restored")
    return details(db, row)


@router.delete("/tasks/{task_id}/permanent")
def permanent(task_id: str, data: s.Confirmation, account: CurrentAccount, db: DB):
    row = owned(db, Task, task_id, account.id, lock=True)
    version(row, data.version)
    if not row.deleted_at:
        raise HTTPException(409, "Move the task to Trash first")
    event(db, row, "permanently_deleted")
    db.delete(row)
    return {"message": "Task permanently deleted"}


@router.get("/tasks/{task_id}/activity")
def activity(task_id: str, account: CurrentAccount, db: DB):
    owned(db, Task, task_id, account.id)
    return [
        {"id": row.id, "event": row.event, "fields": row.fields, "occurred_at": row.occurred_at}
        for row in db.scalars(
            select(Activity)
            .where(Activity.task_id == task_id, Activity.account_id == account.id)
            .order_by(Activity.occurred_at.desc())
            .limit(200)
        )
    ]


@router.get("/tags")
def tags(account: CurrentAccount, db: DB):
    return [
        {"id": row.id, "name": row.name}
        for row in db.scalars(select(Tag).where(Tag.account_id == account.id).order_by(Tag.name))
    ]


@router.post("/tags", status_code=201)
def create_tag(data: s.TagInput, account: CurrentAccount, db: DB):
    name = data.name.casefold()
    if db.scalar(select(Tag.id).where(Tag.account_id == account.id, Tag.normalized_name == name)):
        raise HTTPException(409, "A tag with this name already exists")
    tag = Tag(account_id=account.id, name=data.name, normalized_name=name)
    db.add(tag)
    db.flush()
    return {"id": tag.id, "name": tag.name}


@router.patch("/tags/{tag_id}")
def rename_tag(tag_id: str, data: s.TagInput, account: CurrentAccount, db: DB):
    tag = owned(db, Tag, tag_id, account.id, lock=True)
    tag.name, tag.normalized_name = data.name, data.name.casefold()
    return {"id": tag.id, "name": tag.name}


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: str, account: CurrentAccount, db: DB):
    db.delete(owned(db, Tag, tag_id, account.id, lock=True))
    return {"message": "Tag deleted"}


@router.post("/bulk")
def bulk(data: s.BulkInput, account: CurrentAccount, db: DB):
    if len({item.id for item in data.items}) != len(data.items):
        raise HTTPException(422, "Select each task only once")
    rows = [
        owned(db, Task, item.id, account.id, lock=True)
        for item in sorted(data.items, key=lambda item: item.id)
    ]
    versions = {item.id: item.version for item in data.items}
    for row in rows:
        version(row, versions[row.id])
        if row.deleted_at:
            raise HTTPException(409, "Restore tasks before applying bulk actions")
    if data.action == "move":
        if not data.list_id:
            raise HTTPException(422, "Choose a destination list")
        owned(db, TaskList, data.list_id, account.id, lock=True)
    if data.action == "priority" and not data.priority:
        raise HTTPException(422, "Choose a priority")
    if data.action == "trash" and not data.confirmed:
        raise HTTPException(422, "Confirm before moving tasks to Trash")
    for row in rows:
        if data.action == "trash":
            trash(db, row)
        else:
            if data.action == "complete":
                if row.status != "COMPLETED":
                    event(db, row, "completed")
                row.status = "COMPLETED"
                row.completed_at = row.completed_at or now()
            elif data.action == "move":
                row.list_id = data.list_id
            else:
                row.priority = data.priority
            row.version += 1
            row.updated_at = now()
            event(db, row, "bulk_" + data.action)
    return {"changed": len(rows)}


@router.get("/dashboard")
def dashboard(account: CurrentAccount, db: DB):
    today = now().astimezone(ZoneInfo(account.timezone)).date()
    rows = db.scalars(
        select(Task).where(Task.account_id == account.id, Task.deleted_at.is_(None))
    ).all()
    return {
        "today": sum(t.status != "COMPLETED" and t.due_date == today for t in rows),
        "upcoming": sum(
            t.status != "COMPLETED" and t.due_date is not None and t.due_date > today for t in rows
        ),
        "overdue": sum(
            t.status != "COMPLETED" and t.due_date is not None and t.due_date < today for t in rows
        ),
        "status": {
            value: sum(t.status == value for t in rows)
            for value in ("TODO", "IN_PROGRESS", "COMPLETED")
        },
    }


@router.get("/reports")
def reports(account: CurrentAccount, db: DB, start: date, end: date):
    if start > end or (end - start).days > 366:
        raise HTTPException(422, "Choose an ordered date range of at most 366 days")
    zone = ZoneInfo(account.timezone)
    rows = db.scalars(
        select(Task).where(Task.account_id == account.id, Task.deleted_at.is_(None))
    ).all()
    counts = {}
    day = start
    while day <= end:
        counts[day.isoformat()] = 0
        day += timedelta(days=1)
    for completed_at in db.scalars(
        select(Activity.occurred_at).where(
            Activity.account_id == account.id, Activity.event == "completed"
        )
    ):
        key = completed_at.astimezone(zone).date().isoformat()
        if key in counts:
            counts[key] += 1
    return {
        "completions": counts,
        "status": {
            value: sum(t.status == value for t in rows)
            for value in ("TODO", "IN_PROGRESS", "COMPLETED")
        },
    }
