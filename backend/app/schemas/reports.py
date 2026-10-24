from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str | None
    export_format: str
    report_kind: str
    result_count: int
    created_at: datetime
