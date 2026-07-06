from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    name: str
    settings: dict = Field(default_factory=dict)


class TenantResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    settings: dict


class CreateTenantResponse(BaseModel):
    tenant: TenantResponse
    api_key: str  # Only returned once on creation
