from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Cadence = Literal["daily", "weekly", "monthly"]


class ScheduleCreate(BaseModel):
    profile_id: str
    connector_ids: list[str] = Field(min_length=1, max_length=25)
    cadence: Cadence
    external_search_consent: bool = False


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    connector_ids: list[str]
    cadence: Cadence
    enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None
    created_at: datetime


class ScheduleUpdate(BaseModel):
    enabled: bool
