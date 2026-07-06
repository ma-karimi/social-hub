from pydantic import BaseModel, Field
from uuid import UUID


class PostContentSchema(BaseModel):
    title: str
    body: str
    price: float | None = None
    currency: str | None = None
    images: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ButtonSchema(BaseModel):
    action: str
    label: str
    payload: dict = Field(default_factory=dict)


class PublishProductRequest(BaseModel):
    platforms: list[str]
    content: PostContentSchema
    buttons: list[ButtonSchema] = Field(default_factory=list)
    external_ref: str | None = None


class PublishNormalRequest(BaseModel):
    platforms: list[str]
    content: PostContentSchema
    external_ref: str | None = None


class EditPostRequest(BaseModel):
    content: PostContentSchema
    buttons: list[ButtonSchema] | None = None


class PublicationStatusSchema(BaseModel):
    id: str
    status: str
    connection_id: str


class PublishResponse(BaseModel):
    post_id: str
    publications: list[PublicationStatusSchema]
    warnings: list[str] = Field(default_factory=list)


class PostResponse(BaseModel):
    id: str
    tenant_id: str
    post_type: str
    status: str
    external_ref: str | None
    publications: list[PublicationStatusSchema] = Field(default_factory=list)
