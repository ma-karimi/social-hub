"""Unit tests for mapper scrubbing, feature gates, i18n, OpenAPI brand safety."""

from uuid import uuid4

import pytest

from social_hub.api.i18n import error_body, resolve_locale, translate
from social_hub.application.services.facebook_feature_gate import (
    assert_facebook_feature_allowed,
    collect_fb_gated_fields,
)
from social_hub.domain.entities.social_account import SocialAccount
from social_hub.domain.error_codes import ErrorCode
from social_hub.domain.exceptions import (
    FeatureDisabledForTenantError,
    FeatureRequiresFacebookLoginError,
)
from social_hub.domain.value_objects.facebook_features import (
    DEFAULT_FACEBOOK_LOGIN_FEATURES,
    resolve_facebook_login_features,
)
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.infrastructure.providers.zernio.mappers import (
    contains_zernio_domain,
    map_presign_response,
    map_quota,
    scrub_urls_in_obj,
)


def test_default_facebook_features_are_enabled():
    assert DEFAULT_FACEBOOK_LOGIN_FEATURES["ads"] is True
    assert all(DEFAULT_FACEBOOK_LOGIN_FEATURES.values())


def test_resolve_features_opt_out():
    settings = {
        "social": {
            "instagram": {
                "facebook_login_features": {"ads": False, "audio_configuration": True}
            }
        }
    }
    feats = resolve_facebook_login_features(settings)
    assert feats["ads"] is False
    assert feats["paid_partnership"] is True


def test_feature_gate_instagram_login_always_blocked():
    account = SocialAccount.create(
        tenant_id=uuid4(),
        platform=PlatformType.INSTAGRAM,
        external_account_id="acc1",
        login_method="instagram_login",
    )
    with pytest.raises(FeatureRequiresFacebookLoginError):
        assert_facebook_feature_allowed(account, {}, "audio_configuration")


def test_feature_gate_facebook_login_disabled_by_tenant():
    account = SocialAccount.create(
        tenant_id=uuid4(),
        platform=PlatformType.INSTAGRAM,
        external_account_id="acc1",
        login_method="facebook_login",
    )
    settings = {
        "social": {"instagram": {"facebook_login_features": {"audio_configuration": False}}}
    }
    with pytest.raises(FeatureDisabledForTenantError):
        assert_facebook_feature_allowed(account, settings, "audio_configuration")


def test_feature_gate_facebook_login_enabled_passes():
    account = SocialAccount.create(
        tenant_id=uuid4(),
        platform=PlatformType.INSTAGRAM,
        external_account_id="acc1",
        login_method="facebook_login",
    )
    assert_facebook_feature_allowed(account, {}, "paid_partnership")


def test_collect_fb_gated_fields():
    fields = collect_fb_gated_fields(
        {
            "audio_configuration": {"audio_id": "1"},
            "is_paid_partnership": True,
            "branded_content_sponsors": ["brand"],
        }
    )
    assert set(fields) == {
        "audio_configuration",
        "is_paid_partnership",
        "branded_content_sponsors",
    }


def test_presign_public_url_uses_relay_not_zernio():
    upstream = {
        "uploadUrl": "https://s3.amazonaws.com/bucket/upload",
        "publicUrl": "https://media.zernio.com/temp/abc_photo.jpg",
        "key": "temp/abc_photo.jpg",
        "expiresIn": 3600,
    }
    payload, key, upstream_public = map_presign_response(
        upstream, relay_base_url="https://api.codenegar.example"
    )
    assert "zernio" not in payload["public_url"].lower()
    assert payload["public_url"].startswith(
        "https://api.codenegar.example/api/v1/social/media/relay/"
    )
    assert contains_zernio_domain(upstream_public)


def test_scrub_urls_removes_zernio():
    obj = {"media_url": "https://media.zernio.com/x.jpg", "ok": "https://cdn.example.com/a.jpg"}
    cleaned = scrub_urls_in_obj(obj)
    assert cleaned["media_url"] == ""
    assert cleaned["ok"] == "https://cdn.example.com/a.jpg"


def test_map_quota():
    assert map_quota({"quotaUsage": 3, "quotaTotal": 50, "quotaDurationSeconds": 86400}) == {
        "quota_usage": 3,
        "quota_total": 50,
        "quota_duration_seconds": 86400,
    }


def test_i18n_locale_and_messages():
    assert resolve_locale("fa-IR,en;q=0.8") == "fa"
    assert resolve_locale(None) == "en"
    assert "Facebook" in translate(ErrorCode.FEATURE_REQUIRES_FACEBOOK_LOGIN, "en")
    assert "Facebook" in translate(ErrorCode.FEATURE_REQUIRES_FACEBOOK_LOGIN, "fa")
    body = error_body(ErrorCode.ACCOUNT_NOT_FOUND, locale="fa")
    assert body["error_code"] == "ACCOUNT_NOT_FOUND"
    assert body["message"]


def test_openapi_has_no_zernio_brand():
    from contextlib import asynccontextmanager

    from social_hub.main import create_app

    @asynccontextmanager
    async def _noop(_app):
        yield

    app = create_app(lifespan_override=_noop)
    schema = app.openapi()
    import json

    dumped = json.dumps(schema).lower()
    assert "zernio" not in dumped
    assert "codenegar" in schema["info"]["title"].lower()
