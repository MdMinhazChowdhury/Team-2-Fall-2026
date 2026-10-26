import calendar
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from celery import Celery
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select

from tasktrack.adapters import queue_mail, send_mail
from tasktrack.config import settings
from tasktrack.db import SessionLocal, now
from tasktrack.models import (
    Account,
    ChecklistItem,
    ExportJob,
    ImportBatch,
    LoginSession,
    Notification,
    Outbox,
    RateBucket,
    Recurrence,
    Reminder,
    Task,
    TaskTag,
    Token,
)
from tasktrack.services import event, export_snapshot

celery = Celery("tasktrack", broker=settings().redis_url)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    beat_schedule={"durable-scan": {"task": "tasktrack.scan", "schedule": 30.0}},
    worker_prefetch_multiplier=1,
)


def following(rule: Recurrence, current: date) -> date:
    if rule.frequency == "daily":
        return current + timedelta(days=rule.interval)
    if rule.frequency == "weekly":
        return current + timedelta(weeks=rule.interval)
    month = current.year * 12 + current.month - 1 + rule.interval
    year, index = divmod(month, 12)
    return date(year, index + 1, min(rule.anchor.day, calendar.monthrange(year, index + 1)[1]))


def run_due(db, clock=None):
    clock = clock or now()
    rules = db.scalars(
        select(Recurrence).where(Recurrence.active.is_(True)).with_for_update(skip_locked=True)
    ).all()
    for rule in rules:
        source = db.get(Task, rule.task_id)
        if source.deleted_at:
            continue
        today = clock.astimezone(ZoneInfo(rule.timezone)).date()
        # Bound each scan; overdue schedules continue catching up on subsequent scans.
        for _ in range(100):
            if rule.end_date and rule.next_date > rule.end_date:
                rule.active = False
                break
            if rule.next_date > today:
                break
            existing = db.scalar(
                select(Task.id).where(
                    Task.recurrence_id == rule.id, Task.occurrence == rule.next_date
                )
            )
            if not existing:
                task = Task(
                    account_id=source.account_id,
                    list_id=source.list_id,
                    title=source.title,
                    description=source.description,
                    due_date=rule.next_date,
                    priority=source.priority,
                    status="TODO",
                    recurrence_id=rule.id,
                    occurrence=rule.next_date,
                )
                db.add(task)
                db.flush()
                for item in db.scalars(
                    select(ChecklistItem).where(ChecklistItem.task_id == source.id)
                ):
                    db.add(
                        ChecklistItem(
                            account_id=source.account_id,
                            task_id=task.id,
                            text=item.text,
                            position=item.position,
                            completed=False,
                        )
                    )
                for tag_id in db.scalars(
                    select(TaskTag.tag_id).where(TaskTag.task_id == source.id)
                ):
                    db.add(TaskTag(account_id=source.account_id, task_id=task.id, tag_id=tag_id))
                event(db, task, "recurrence_created")
            try:
                rule.next_date = following(rule, rule.next_date)
            except (ValueError, OverflowError):
                rule.active = False
                break
    reminders = db.scalars(
        select(Reminder)
        .where(Reminder.delivered_at.is_(None), Reminder.scheduled_at <= clock)
        .with_for_update(skip_locked=True)
    ).all()
    for reminder in reminders:
        task = db.get(Task, reminder.task_id)
        if task.deleted_at or task.status == "COMPLETED":
            reminder.delivered_at = clock
            continue
        key = "reminder:" + reminder.id
        if not db.scalar(select(Notification.id).where(Notification.delivery_key == key)):
            db.add(
                Notification(
                    account_id=reminder.account_id,
                    delivery_key=key,
                    task_id=task.id,
                    title=task.title,
                )
            )
            account = db.get(Account, reminder.account_id)
            if reminder.email and account.email_reminders and account.verified_at:
                queue_mail(
                    db,
                    account.id,
                    account.email,
                    "TaskTrack reminder",
                    "A task reminder is due. Open TaskTrack to see your task.",
                    key,
                )
        reminder.delivered_at = clock
    for task in db.scalars(
        select(Task).where(Task.purge_after <= clock).with_for_update(skip_locked=True)
    ):
        event(db, task, "purged")
        db.delete(task)
    db.execute(delete(Token).where(Token.expires_at < clock))
    db.execute(delete(LoginSession).where(LoginSession.expires_at < clock))
    db.execute(delete(RateBucket).where(RateBucket.window < int(clock.timestamp()) // 60 - 60))


def deliver_outbox(db, clock=None):
    clock = clock or now()
    for mail in db.scalars(
        select(Outbox)
        .where(Outbox.status == "pending", Outbox.next_attempt_at <= clock)
        .with_for_update(skip_locked=True)
        .limit(25)
    ):
        try:
            send_mail(mail.encrypted_payload, mail.delivery_key)
        except Exception:
            mail.attempts += 1
            mail.error_code = "smtp_delivery_failed"
            mail.next_attempt_at = clock + timedelta(seconds=min(3600, 2**mail.attempts * 30))
            if mail.attempts >= 5:
                mail.status = "failed"
        else:
            mail.status = "delivered"
            mail.encrypted_payload = ""


def run_exports(db):
    for job in db.scalars(
        select(ExportJob)
        .where(ExportJob.status == "pending", ExportJob.expires_at > now())
        .with_for_update(skip_locked=True)
        .limit(10)
    ):
        try:
            job.payload = jsonable_encoder(export_snapshot(db, job.account_id))
        except HTTPException:
            job.status = "failed"
            job.error_code = "export_limit_exceeded"
        else:
            job.status = "ready"
    db.execute(delete(ExportJob).where(ExportJob.expires_at <= now()))
    db.execute(delete(ImportBatch).where(ImportBatch.expires_at <= now()))


@celery.task(name="tasktrack.scan", autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def scan():
    with SessionLocal.begin() as db:
        run_due(db)
    with SessionLocal.begin() as db:
        deliver_outbox(db)
    with SessionLocal.begin() as db:
        db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        run_exports(db)
