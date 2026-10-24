from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str | None
    kind: str
    title: str
    message: str
    read_at: datetime | None
    created_at: datetime


class NotificationPreferenceRead(BaseModel):
    notify_new_mentions: bool


class NotificationPreferenceUpdate(BaseModel):
    notify_new_mentions: bool
