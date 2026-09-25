from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.exceptions import (
    FeatureDisabledForTenantError,
    FeatureRequiresFacebookLoginError,
)
from social_hub.domain.value_objects.facebook_features import (
    FB_FEATURE_FIELD_MAP,
    resolve_facebook_login_features,
)


def assert_facebook_feature_allowed(
    account: SocialAccount,
    tenant_settings: dict | None,
    feature_key: str,
) -> None:
    """Gate FB-only features.

    - instagram_login accounts always rejected
    - facebook_login accounts rejected when tenant disabled the feature (default enabled)
    """
    if account.login_method != "facebook_login":
        raise FeatureRequiresFacebookLoginError(feature_key)

    features = resolve_facebook_login_features(tenant_settings)
    config_key = FB_FEATURE_FIELD_MAP.get(feature_key, feature_key)
    if not features.get(config_key, True):
        raise FeatureDisabledForTenantError(feature_key)


def collect_fb_gated_fields(platform_specific_data: dict) -> list[str]:
    gated = []
    if platform_specific_data.get("audio_configuration"):
        gated.append("audio_configuration")
    if platform_specific_data.get("is_paid_partnership"):
        gated.append("is_paid_partnership")
    if platform_specific_data.get("branded_content_sponsors"):
        gated.append("branded_content_sponsors")
    return gated
