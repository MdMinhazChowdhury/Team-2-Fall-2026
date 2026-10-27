from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from tasktrack.db import Base, now


def uuid() -> str:
    return str(uuid4())


class Identity:
    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid)


class Account(Identity, Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("role IN ('USER','ADMIN')"),)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default="USER")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    email_reminders: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LoginSession(Identity, Base):
    __tablename__ = "sessions"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user_agent: Mapped[str] = mapped_column(String(200), default="")


class Token(Identity, Base):
    __tablename__ = "tokens"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskList(Identity, Base):
    __tablename__ = "lists"
    __table_args__ = (
        UniqueConstraint("id", "account_id"),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 100"),
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Task(Identity, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("id", "account_id"),
        ForeignKeyConstraint(
            ["list_id", "account_id"], ["lists.id", "lists.account_id"], ondelete="CASCADE"
        ),
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 200"),
        CheckConstraint("status IN ('TODO','IN_PROGRESS','COMPLETED')"),
        CheckConstraint("priority IN ('LOW','MEDIUM','HIGH')"),
        UniqueConstraint("recurrence_id", "occurrence"),
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    list_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(16), default="TODO")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recurrence_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    occurrence: Mapped[date | None] = mapped_column(Date)


class ChecklistItem(Identity, Base):
    __tablename__ = "checklist_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "account_id"], ["tasks.id", "tasks.account_id"], ondelete="CASCADE"
        ),
    )
    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), index=True)
    text: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class Tag(Identity, Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("id", "account_id"),
        UniqueConstraint("account_id", "normalized_name"),
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(40))
    normalized_name: Mapped[str] = mapped_column(String(40))


class TaskTag(Base):
    __tablename__ = "task_tags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "account_id"], ["tasks.id", "tasks.account_id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["tag_id", "account_id"], ["tags.id", "tags.account_id"], ondelete="CASCADE"
        ),
    )
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    tag_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))


class Activity(Identity, Base):
    __tablename__ = "activity"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), index=True)
    event: Mapped[str] = mapped_column(String(40))
    fields: Mapped[list] = mapped_column(JSON, default=list)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Recurrence(Identity, Base):
    __tablename__ = "recurrences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "account_id"], ["tasks.id", "tasks.account_id"], ondelete="CASCADE"
        ),
    )
    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), unique=True)
    frequency: Mapped[str] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    interval: Mapped[int] = mapped_column(Integer, default=1)
    anchor: Mapped[date] = mapped_column(Date)
    next_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Reminder(Identity, Base):
    __tablename__ = "reminders"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "account_id"], ["tasks.id", "tasks.account_id"], ondelete="CASCADE"
        ),
    )
    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    email: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Identity, Base):
    __tablename__ = "notifications"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    delivery_key: Mapped[str] = mapped_column(String(100), unique=True)
    task_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False))
    title: Mapped[str] = mapped_column(String(200))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ImportBatch(Identity, Base):
    __tablename__ = "import_batches"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    payload: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExportJob(Identity, Base):
    __tablename__ = "export_jobs"
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    payload: Mapped[dict | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(40))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Outbox(Identity, Base):
    __tablename__ = "outbox"
    delivery_key: Mapped[str] = mapped_column(String(100), unique=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    error_code: Mapped[str | None] = mapped_column(String(40))


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer, default=1)
