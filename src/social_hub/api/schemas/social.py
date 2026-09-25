from pydantic import BaseModel, Field


FB_NOTE_EN = "Requires Facebook Login connection"
FB_NOTE_FA = "نیازمند اتصال با Facebook Login"


class ConnectAccountRequest(BaseModel):
    platform: str = Field(..., description="instagram | telegram | bale | eitaa")
    redirect_url: str | None = Field(
        None, description="OAuth callback for the consumer UI (Instagram)"
    )
    login_method: str | None = Field(
        "instagram_login",
        description="instagram_login (default) or facebook_login",
    )
    mode: str | None = Field(
        "headless",
        description="headless (default) or standard — Instagram only",
    )
    credentials: dict | None = Field(
        None, description="Bot credentials for telegram/bale/eitaa"
    )
    settings: dict | None = Field(
        None, description="Platform settings e.g. channel_id"
    )


class ConnectStartResponse(BaseModel):
    auth_url: str | None = None
    account_id: str | None = None
    mode: str


class SelectPageRequest(BaseModel):
    connect_token: str
    page_id: str
    platform: str = "instagram"


class PageOptionResponse(BaseModel):
    page_id: str
    name: str


class SocialAccountResponse(BaseModel):
    id: str
    tenant_id: str
    platform: str
    external_account_id: str
    login_method: str | None = None
    display_name: str | None = None
    username: str | None = None
    settings: dict = Field(default_factory=dict)
    is_active: bool = True


class UpdateAccountRequest(BaseModel):
    settings: dict | None = None
    credentials: dict | None = None
    is_active: bool | None = None


class FacebookLoginFeatures(BaseModel):
    ads: bool = True
    audio_configuration: bool = True
    paid_partnership: bool = True
    branded_content_sponsors: bool = True


class InstagramConfigResponse(BaseModel):
    facebook_login_features: FacebookLoginFeatures


class InstagramConfigUpdateRequest(BaseModel):
    facebook_login_features: FacebookLoginFeatures | None = None


class MediaItemSchema(BaseModel):
    url: str
    type: str | None = Field(None, description="image | video | gif | document")


class UserTagSchema(BaseModel):
    username: str
    x: float | None = None
    y: float | None = None
    media_index: int | None = 0


class AudioConfigurationSchema(BaseModel):
    audio_id: str = Field(..., description=FB_NOTE_EN)
    audio_volume: int = 100
    video_volume: int = 100


class PlatformSpecificDataSchema(BaseModel):
    content_type: str | None = Field(None, description="Set to 'story' for Stories")
    share_to_feed: bool | None = True
    collaborators: list[str] | None = None
    user_tags: list[UserTagSchema] | None = None
    trial_params: dict | None = None
    thumb_offset: int | None = None
    instagram_thumbnail: str | None = None
    reel_cover: str | None = None
    audio_name: str | None = None
    audio_configuration: AudioConfigurationSchema | None = Field(
        None, description=FB_NOTE_EN
    )
    mute_audio: bool | None = False
    is_ai_generated: bool | None = False
    is_paid_partnership: bool | None = Field(None, description=FB_NOTE_EN)
    branded_content_sponsors: list[str] | None = Field(None, description=FB_NOTE_EN)
    comments_enabled: bool | None = True
    location_id: str | None = None
    first_comment: str | None = None


class ButtonSchema(BaseModel):
    action: str = "callback"
    label: str
    payload: dict = Field(default_factory=dict)


class CreateSocialPostRequest(BaseModel):
    account_ids: list[str]
    content: str | None = None
    title: str | None = None
    media_items: list[MediaItemSchema] = Field(default_factory=list)
    publish_now: bool = False
    scheduled_for: str | None = None
    is_draft: bool = False
    timezone: str = Field(
        "Asia/Tehran",
        description="IANA timezone for scheduled_for values without offset",
    )
    platform_specific_data: PlatformSpecificDataSchema | None = None
    metadata: dict | None = None
    external_ref: str | None = None
    price: float | None = None
    currency: str | None = None
    buttons: list[ButtonSchema] = Field(default_factory=list)


class PlatformResultSchema(BaseModel):
    account_id: str
    platform: str
    status: str
    platform_post_url: str | None = None
    platform_message_id: str | None = None
    error: str | None = None


class SocialPostResponse(BaseModel):
    post_id: str
    status: str
    platforms: list[PlatformResultSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MediaPresignRequest(BaseModel):
    filename: str
    content_type: str


class MediaPresignResponse(BaseModel):
    upload_url: str
    public_url: str
    key: str
    expires_in: int = 3600


class PublishingQuotaResponse(BaseModel):
    quota_usage: int | None = None
    quota_total: int | None = None
    quota_duration_seconds: int | None = None


class IceBreakersRequest(BaseModel):
    ice_breakers: list[str]
