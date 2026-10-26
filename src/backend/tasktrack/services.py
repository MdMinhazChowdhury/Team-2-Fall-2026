import json
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tasktrack.db import now
from tasktrack.models import Activity, ChecklistItem, Tag, Task, TaskList, TaskTag
from tasktrack.schemas import TaskInput, TaskUpdate


def owned(db: Session, model: Any, record_id: str, account_id: str, *, lock=False):
    try:
        UUID(record_id)
    except ValueError as error:
        raise HTTPException(404, "Item not found") from error
    query = select(model).where(model.id == record_id, model.account_id == account_id)
    if lock:
        query = query.with_for_update()
    record = db.scalar(query)
    if record is None:
        raise HTTPException(404, "Item not found")
    return record


def version(record: Any, expected: int):
    if record.version != expected:
        raise HTTPException(409, "This item changed. Refresh before saving again.")


def event(db: Session, task: Task, kind: str, fields: list[str] | None = None):
    db.add(Activity(account_id=task.account_id, task_id=task.id, event=kind, fields=fields or []))


def details(db: Session, task: Task) -> dict:
    return {
        "id": task.id,
        "list_id": task.list_id,
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date,
        "status": task.status,
        "priority": task.priority,
        "version": task.version,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "deleted_at": task.deleted_at,
        "purge_after": task.purge_after,
        "checklist": [
            {"text": item.text, "completed": item.completed}
            for item in db.scalars(
                select(ChecklistItem)
                .where(
                    ChecklistItem.task_id == task.id, ChecklistItem.account_id == task.account_id
                )
                .order_by(ChecklistItem.position)
            )
        ],
        "tag_ids": list(
            db.scalars(
                select(TaskTag.tag_id).where(
                    TaskTag.task_id == task.id, TaskTag.account_id == task.account_id
                )
            )
        ),
    }


def save_task(db: Session, account_id: str, data: TaskInput, task: Task | None = None) -> Task:
    creating = task is None
    owned(db, TaskList, data.list_id, account_id, lock=True)
    tags = set(data.tag_ids)
    for tag_id in sorted(tags):
        owned(db, Tag, tag_id, account_id)
    if task:
        if not isinstance(data, TaskUpdate):
            raise ValueError("Expected versioned update")
        version(task, data.version)
        if task.deleted_at:
            raise HTTPException(409, "Restore the task before editing it")
        fields = [
            key
            for key in ("list_id", "title", "description", "due_date", "priority", "status")
            if getattr(task, key) != getattr(data, key)
        ]
        kind = (
            "completed"
            if data.status == "COMPLETED" and task.status != "COMPLETED"
            else "reopened"
            if task.status == "COMPLETED" and data.status != "COMPLETED"
            else "edited"
        )
        task.version += 1
    else:
        task = Task(account_id=account_id)
        db.add(task)
        kind = "created"
        fields = []
    for key in ("list_id", "title", "description", "due_date", "priority", "status"):
        setattr(task, key, getattr(data, key))
    task.updated_at = now()
    task.completed_at = (task.completed_at or now()) if data.status == "COMPLETED" else None
    db.flush()
    db.execute(
        delete(ChecklistItem).where(
            ChecklistItem.task_id == task.id, ChecklistItem.account_id == account_id
        )
    )
    db.execute(delete(TaskTag).where(TaskTag.task_id == task.id, TaskTag.account_id == account_id))
    for index, item in enumerate(data.checklist):
        db.add(
            ChecklistItem(
                account_id=account_id,
                task_id=task.id,
                text=item.text,
                completed=item.completed,
                position=index,
            )
        )
    for tag_id in tags:
        db.add(TaskTag(account_id=account_id, task_id=task.id, tag_id=tag_id))
    event(db, task, kind, fields)
    if creating and task.status == "COMPLETED":
        event(db, task, "completed")
    db.flush()
    return task


def trash(db: Session, task: Task):
    if task.deleted_at:
        raise HTTPException(409, "Task is already in Trash")
    task.deleted_at = now()
    task.purge_after = now() + timedelta(days=30)
    task.version += 1
    event(db, task, "trashed")


def export_snapshot(db: Session, account_id: str) -> dict:
    lists = db.scalars(select(TaskList).where(TaskList.account_id == account_id)).all()
    tags = db.scalars(select(Tag).where(Tag.account_id == account_id)).all()
    tasks = db.scalars(
        select(Task).where(Task.account_id == account_id, Task.deleted_at.is_(None))
    ).all()
    if len(lists) > 100 or len(tags) > 500 or len(tasks) > 5000:
        raise HTTPException(422, "This export exceeds the supported file limits")
    result: dict[str, Any] = {
        "format": "tasktrack",
        "version": 1,
        "lists": [{"key": item.id, "name": item.name} for item in lists],
        "tags": [{"key": tag.id, "name": tag.name} for tag in tags],
        "tasks": [],
    }
    for task in tasks:
        value = details(db, task)
        result["tasks"].append({key: value[key] for key in TaskInput.model_fields})
    if (
        len(json.dumps(jsonable_encoder(result), indent=2, ensure_ascii=False).encode("utf8"))
        > 2 * 1024 * 1024
    ):
        raise HTTPException(422, "This export exceeds the supported 2 MiB file limit")
    return result
