"""Default Instagram Facebook-Login feature flags (opt-out model)."""

DEFAULT_FACEBOOK_LOGIN_FEATURES: dict[str, bool] = {
    "ads": True,
    "audio_configuration": True,
    "paid_partnership": True,
    "branded_content_sponsors": True,
}

FB_GATED_POST_FIELDS = frozenset(
    {
        "audio_configuration",
        "is_paid_partnership",
        "branded_content_sponsors",
    }
)

FB_FEATURE_FIELD_MAP = {
    "audio_configuration": "audio_configuration",
    "is_paid_partnership": "paid_partnership",
    "branded_content_sponsors": "branded_content_sponsors",
    "ads": "ads",
}


def resolve_facebook_login_features(tenant_settings: dict | None) -> dict[str, bool]:
    social = (tenant_settings or {}).get("social") or {}
    ig = social.get("instagram") or {}
    raw = ig.get("facebook_login_features") or {}
    return {**DEFAULT_FACEBOOK_LOGIN_FEATURES, **{k: bool(v) for k, v in raw.items()}}
