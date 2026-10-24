from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class AdminOverviewRead(BaseModel):
    application_version: str
    environment: str
    database_backend: str
    cookie_secure: bool
    github_token_configured: bool
    backup_command_available: bool


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, object]
    created_at: datetime


class AuditEventPageRead(BaseModel):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int
    pages: int


class ConnectorSecretWrite(BaseModel):
    value: SecretStr = Field(min_length=1, max_length=1000)


class ConnectorSecretRead(BaseModel):
    connector_id: str
    configured: bool
    key_version: str | None
    updated_at: datetime | None


class ConnectorSecretRotationRead(BaseModel):
    rotated: int
    active_key_version: str


class ConnectorConfigurationUpdate(BaseModel):
    enabled: bool


class ConnectorConfigurationRead(BaseModel):
    connector_id: str
    enabled: bool
    updated_at: datetime
