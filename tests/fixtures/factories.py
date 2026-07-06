"""Test object factories for common domain entities."""
import uuid

from social_hub.domain.entities.button import Button
from social_hub.domain.entities.platform_connection import PlatformConnection
from social_hub.domain.entities.post import Post, PostContent
from social_hub.domain.entities.publication import Publication
from social_hub.domain.entities.tenant import Tenant
from social_hub.domain.value_objects.button_action import ButtonAction
from social_hub.domain.value_objects.platform_type import PlatformType
from social_hub.domain.value_objects.post_type import PostType
from social_hub.domain.value_objects.publication_status import PublicationStatus


def make_tenant(**kwargs) -> Tenant:
    defaults = dict(
        id=uuid.uuid4(),
        name="Test Store",
        api_key_hash="a" * 64,
        is_active=True,
        settings={"webhook_callback_url": "https://panel.example.com/webhooks/socialhub"},
    )
    return Tenant(**{**defaults, **kwargs})


def make_connection(tenant_id=None, **kwargs) -> PlatformConnection:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        platform_type=PlatformType.TELEGRAM,
        credentials_encrypted=b"encrypted_data",
        settings={"channel_id": "@test_channel"},
        is_active=True,
    )
    return PlatformConnection(**{**defaults, **kwargs})


def make_post(tenant_id=None, **kwargs) -> Post:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        post_type=PostType.PRODUCT,
        content=PostContent(
            title="Test Product",
            body="Great product",
            price=150000,
            currency="IRR",
            images=["https://example.com/image.jpg"],
        ),
        status="draft",
        external_ref="product-001",
    )
    return Post(**{**defaults, **kwargs})


def make_publication(post_id=None, connection_id=None, **kwargs) -> Publication:
    defaults = dict(
        id=uuid.uuid4(),
        post_id=post_id or uuid.uuid4(),
        connection_id=connection_id or uuid.uuid4(),
        status=PublicationStatus.PENDING,
    )
    return Publication(**{**defaults, **kwargs})


def make_button(post_id=None, **kwargs) -> Button:
    defaults = dict(
        id=uuid.uuid4(),
        post_id=post_id or uuid.uuid4(),
        action_type=ButtonAction.BUY,
        label="خرید",
        payload={"product_id": 1},
        sort_order=0,
        short_id="testshrt",
    )
    return Button(**{**defaults, **kwargs})
