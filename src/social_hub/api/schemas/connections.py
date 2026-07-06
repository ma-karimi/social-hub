from pydantic import BaseModel, Field


class CreateConnectionRequest(BaseModel):
    platform_type: str
    credentials: dict
    settings: dict = Field(default_factory=dict)


class UpdateConnectionRequest(BaseModel):
    credentials: dict | None = None
    settings: dict | None = None
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    id: str
    tenant_id: str
    platform_type: str
    settings: dict
    is_active: bool
