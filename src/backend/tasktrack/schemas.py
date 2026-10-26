from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Password = Annotated[str, Field(min_length=12, max_length=128)]
Status = Literal["TODO", "IN_PROGRESS", "COMPLETED"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]


class Credentials(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    password: Password


class EmailInput(Input):
    email: EmailStr


class TokenInput(Input):
    token: str = Field(min_length=32, max_length=200)


class Recovery(TokenInput):
    password: Password


class ListInput(Input):
    name: Name


class ListUpdate(ListInput):
    version: int = Field(ge=1)


class ChecklistInput(Input):
    text: Title
    completed: bool = False


class TaskInput(Input):
    list_id: str
    title: Title
    description: str = Field(default="", max_length=5000)
    due_date: date | None = None
    status: Status = "TODO"
    priority: Priority = "MEDIUM"
    checklist: list[ChecklistInput] = Field(default_factory=list, max_length=100)
    tag_ids: list[str] = Field(default_factory=list, max_length=50)


class TaskUpdate(TaskInput):
    version: int = Field(ge=1)


class Confirmation(Input):
    confirmed: Literal[True]
    version: int = Field(ge=1)


class Preferences(Input):
    timezone: str
    email_reminders: bool

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Choose a valid IANA timezone") from error
        return value


class PasswordChange(Input):
    current_password: str = Field(max_length=128)
    new_password: Password


class AccountDeletion(Input):
    current_password: str = Field(max_length=128)
    confirmed: Literal[True]


class TagInput(Input):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class BulkItem(Input):
    id: str
    version: int = Field(ge=1)


class BulkInput(Input):
    items: list[BulkItem] = Field(min_length=1, max_length=100)
    action: Literal["complete", "move", "priority", "trash"]
    list_id: str | None = None
    priority: Priority | None = None
    confirmed: bool = False


class RecurrenceInput(Input):
    frequency: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1, le=365)
    start: date
    end_date: date | None = None


class ReminderInput(Input):
    scheduled_at: datetime
    email: bool = False


class ExportTask(TaskInput):
    list_id: str


class ExportList(Input):
    key: str = Field(min_length=1, max_length=100)
    name: Name


class ExportTag(Input):
    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=40)


class PortableData(Input):
    format: Literal["tasktrack"]
    version: Literal[1]
    lists: list[ExportList] = Field(max_length=100)
    tags: list[ExportTag] = Field(default_factory=list, max_length=500)
    tasks: list[ExportTask] = Field(max_length=5000)
