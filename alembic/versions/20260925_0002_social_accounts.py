"""social accounts and provider tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("login_method", sa.String(50), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("credentials_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "platform", "external_account_id", name="uq_tenant_platform_external"
        ),
    )
    op.create_index("ix_social_accounts_tenant_id", "social_accounts", ["tenant_id"])

    op.create_table(
        "tenant_provider_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("profile_id", sa.String(255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", name="uq_tenant_provider"),
    )
    op.create_index(
        "ix_tenant_provider_credentials_tenant_id",
        "tenant_provider_credentials",
        ["tenant_id"],
    )

    op.create_table(
        "connect_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("our_connect_token", sa.String(64), nullable=False),
        sa.Column("upstream_connect_token", sa.String(255), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("consumer_redirect_url", sa.String(2000), nullable=False),
        sa.Column("login_method", sa.String(50), nullable=False),
        sa.Column("mode", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("our_connect_token"),
    )
    op.create_index(
        "ix_connect_sessions_our_connect_token", "connect_sessions", ["our_connect_token"]
    )
    op.create_index("ix_connect_sessions_tenant_id", "connect_sessions", ["tenant_id"])

    op.create_table(
        "media_relay_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opaque_key", sa.String(64), nullable=False),
        sa.Column("upstream_path", sa.String(2000), nullable=False),
        sa.Column("upstream_public_url", sa.String(2000), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opaque_key"),
    )
    op.create_index("ix_media_relay_keys_opaque_key", "media_relay_keys", ["opaque_key"])

    # Repoint publications from platform_connections → social_accounts
    op.drop_constraint("publications_connection_id_fkey", "publications", type_="foreignkey")
    op.alter_column("publications", "connection_id", new_column_name="account_id")
    op.create_foreign_key(
        "publications_account_id_fkey",
        "publications",
        "social_accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index("ix_publications_connection_id", table_name="publications")
    op.create_index("ix_publications_account_id", "publications", ["account_id"])

    op.drop_table("platform_connections")


def downgrade() -> None:
    op.create_table(
        "platform_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_type", sa.String(50), nullable=False),
        sa.Column("credentials_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "platform_type", name="uq_tenant_platform"),
    )

    op.drop_constraint("publications_account_id_fkey", "publications", type_="foreignkey")
    op.alter_column("publications", "account_id", new_column_name="connection_id")
    op.create_foreign_key(
        "publications_connection_id_fkey",
        "publications",
        "platform_connections",
        ["connection_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_table("media_relay_keys")
    op.drop_table("connect_sessions")
    op.drop_table("tenant_provider_credentials")
    op.drop_table("social_accounts")
