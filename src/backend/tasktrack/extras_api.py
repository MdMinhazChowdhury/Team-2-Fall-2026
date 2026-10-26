from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from tasktrack import schemas as s
from tasktrack.db import now
from tasktrack.models import (
    ExportJob,
    ImportBatch,
    Notification,
    Recurrence,
    Reminder,
    Tag,
    Task,
    TaskList,
)
from tasktrack.security import DB, CurrentAccount, csrf
from tasktrack.services import event, export_snapshot, owned, save_task

router = APIRouter(prefix="/api", dependencies=[Depends(csrf)])


@router.get("/tasks/{task_id}/schedule")
def schedules(task_id: str, account: CurrentAccount, db: DB):
    owned(db, Task, task_id, account.id)
    rule = db.scalar(
        select(Recurrence).where(Recurrence.task_id == task_id, Recurrence.account_id == account.id)
    )
    reminders = db.scalars(
        select(Reminder).where(Reminder.task_id == task_id, Reminder.account_id == account.id)
    ).all()
    return {
        "recurrence": {
            "id": rule.id,
            "frequency": rule.frequency,
            "interval": rule.interval,
            "next_date": rule.next_date,
            "end_date": rule.end_date,
            "active": rule.active,
        }
        if rule
        else None,
        "reminders": [
            {
                "id": row.id,
                "scheduled_at": row.scheduled_at,
                "email": row.email,
                "delivered_at": row.delivered_at,
            }
            for row in reminders
        ],
    }


@router.put("/tasks/{task_id}/recurrence")
def recurrence(task_id: str, data: s.RecurrenceInput, account: CurrentAccount, db: DB):
    task = owned(db, Task, task_id, account.id, lock=True)
    if task.deleted_at or data.end_date and data.end_date < data.start:
        raise HTTPException(422, "Choose a valid active task and ordered recurrence dates")
    row = db.scalar(select(Recurrence).where(Recurrence.task_id == task.id))
    if row:
        # Stop/recreate rather than resetting a rule and reusing occurrence keys.
        raise HTTPException(409, "Remove the existing schedule before replacing it")
    row = Recurrence(
        account_id=account.id,
        task_id=task.id,
        timezone=account.timezone,
        frequency=data.frequency,
        interval=data.interval,
        anchor=data.start,
        next_date=data.start,
        end_date=data.end_date,
    )
    db.add(row)
    event(db, task, "recurrence_configured")
    return {"message": "Recurring schedule saved"}


@router.delete("/tasks/{task_id}/recurrence")
def remove_recurrence(task_id: str, account: CurrentAccount, db: DB):
    owned(db, Task, task_id, account.id, lock=True)
    row = db.scalar(select(Recurrence).where(Recurrence.task_id == task_id).with_for_update())
    if row:
        db.delete(row)
    return {"message": "Schedule removed; generated tasks are retained"}


@router.post("/tasks/{task_id}/reminders", status_code=201)
def reminder(task_id: str, data: s.ReminderInput, account: CurrentAccount, db: DB):
    task = owned(db, Task, task_id, account.id, lock=True)
    scheduled = data.scheduled_at
    if scheduled.tzinfo is None:
        zone = ZoneInfo(account.timezone)
        first = scheduled.replace(tzinfo=zone, fold=0)
        second = scheduled.replace(tzinfo=zone, fold=1)
        if first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != scheduled:
            raise HTTPException(
                422, "This local time does not exist because clocks change. Choose another time."
            )
        if first.utcoffset() != second.utcoffset():
            raise HTTPException(
                422,
                "This local time occurs twice. Include an explicit UTC offset, such as -04:00 or -05:00.",
            )
        scheduled = first
    scheduled = scheduled.astimezone(UTC)
    if task.deleted_at or scheduled <= now():
        raise HTTPException(422, "Choose a future reminder for an active task")
    if data.email and not account.email_reminders:
        raise HTTPException(422, "Enable email reminders in settings first")
    row = Reminder(account_id=account.id, task_id=task.id, scheduled_at=scheduled, email=data.email)
    db.add(row)
    db.flush()
    return {"id": row.id, "message": "Reminder saved"}


@router.delete("/reminders/{reminder_id}")
def cancel_reminder(reminder_id: str, account: CurrentAccount, db: DB):
    db.delete(owned(db, Reminder, reminder_id, account.id, lock=True))
    return {"message": "Reminder cancelled"}


@router.get("/notifications")
def notifications(account: CurrentAccount, db: DB):
    return [
        {
            "id": row.id,
            "task_id": row.task_id,
            "title": row.title,
            "read_at": row.read_at,
            "created_at": row.created_at,
        }
        for row in db.scalars(
            select(Notification)
            .where(Notification.account_id == account.id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    ]


@router.post("/notifications/{notification_id}/read")
def read(notification_id: str, account: CurrentAccount, db: DB):
    row = owned(db, Notification, notification_id, account.id, lock=True)
    row.read_at = now()
    return {"message": "Notification marked read"}


@router.get("/export")
def export(account: CurrentAccount, db: DB, response: Response):
    response.headers["Content-Disposition"] = 'attachment; filename="tasktrack-export.json"'
    return export_snapshot(db, account.id)


@router.post("/exports", status_code=202)
def queue_export(account: CurrentAccount, db: DB):
    job = ExportJob(account_id=account.id, expires_at=now() + timedelta(hours=1))
    db.add(job)
    db.flush()
    return {"id": job.id, "status": job.status}


@router.get("/exports/{job_id}")
def export_status(job_id: str, account: CurrentAccount, db: DB):
    job = owned(db, ExportJob, job_id, account.id)
    if job.expires_at <= now():
        raise HTTPException(410, "Export expired. Request another export.")
    return {"id": job.id, "status": job.status, "error_code": job.error_code}


@router.get("/exports/{job_id}/download")
def download_export(job_id: str, account: CurrentAccount, db: DB, response: Response):
    job = owned(db, ExportJob, job_id, account.id)
    if job.expires_at <= now() or job.status != "ready":
        raise HTTPException(409, "Export is not ready or has expired")
    response.headers["Content-Disposition"] = 'attachment; filename="tasktrack-export.json"'
    return job.payload


def validate_import(data: s.PortableData):
    lists = {item.key for item in data.lists}
    tags = {item.key for item in data.tags}
    if (
        len(lists) != len(data.lists)
        or len(tags) != len(data.tags)
        or len({item.name.casefold() for item in data.tags}) != len(data.tags)
    ):
        raise HTTPException(422, "Duplicate list/tag keys or tag names")
    if any(task.list_id not in lists or not set(task.tag_ids) <= tags for task in data.tasks):
        raise HTTPException(422, "Every task must refer to a list and tags present in this file")


@router.post("/import/preview")
def preview(data: s.PortableData, account: CurrentAccount, db: DB):
    validate_import(data)
    batch = ImportBatch(
        account_id=account.id,
        payload=jsonable_encoder(data),
        expires_at=now() + timedelta(minutes=15),
    )
    db.add(batch)
    db.flush()
    return {
        "id": batch.id,
        "lists": len(data.lists),
        "tasks": len(data.tasks),
        "tags": len(data.tags),
        "expires_at": batch.expires_at,
        "message": "Adds new lists and tasks; matching tag names are reused. No data has been imported yet.",
    }


@router.post("/import/{batch_id}/apply")
def apply_import(batch_id: str, account: CurrentAccount, db: DB):
    batch = owned(db, ImportBatch, batch_id, account.id, lock=True)
    if batch.applied_at or batch.expires_at <= now():
        raise HTTPException(409, "Import preview already used or expired; preview the file again")
    data = s.PortableData.model_validate(batch.payload)
    validate_import(data)
    lists, tags = {}, {}
    for item in data.lists:
        row = TaskList(account_id=account.id, name=item.name)
        db.add(row)
        db.flush()
        lists[item.key] = row.id
    for tag_data in data.tags:
        tag = db.scalar(
            select(Tag).where(
                Tag.account_id == account.id, Tag.normalized_name == tag_data.name.casefold()
            )
        )
        if not tag:
            tag = Tag(
                account_id=account.id, name=tag_data.name, normalized_name=tag_data.name.casefold()
            )
            db.add(tag)
            db.flush()
        tags[tag_data.key] = tag.id
    for task in data.tasks:
        payload = task.model_copy(
            update={"list_id": lists[task.list_id], "tag_ids": [tags[key] for key in task.tag_ids]}
        )
        save_task(db, account.id, payload)
    batch.applied_at = now()
    batch.payload = {}
    return {"message": f"Imported {len(data.tasks)} tasks in one transaction"}
