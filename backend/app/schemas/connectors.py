from datetime import datetime

from pydantic import BaseModel

from app.connectors.base import IdentifierType


class ConnectorRead(BaseModel):
    identifier: str
    version: str
    capabilities: list[str]
    accepted_identifiers: list[IdentifierType]
    requires_api_key: bool
    enabled: bool
    ready: bool
    health: str
    rate_limit_per_minute: int | None
    quota_status: str
    last_scan_at: datetime | None
    result_count: int
    error_count: int
