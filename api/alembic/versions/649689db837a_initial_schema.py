"""initial schema

Revision ID: 649689db837a
Revises:
Create Date: 2026-11-03 00:07:59.724336

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "649689db837a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "businesses",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("cac_number", sa.Text(), nullable=False),
        sa.Column("tin", sa.Text(), nullable=False),
        sa.Column(
            "sector",
            sa.Enum(
                "agriculture",
                "retail",
                "manufacturing",
                "logistics",
                "technology",
                "healthcare",
                "hospitality",
                "construction",
                "fashion",
                "education",
                name="sector",
            ),
            nullable=False,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("director_name", sa.Text(), nullable=False),
        sa.Column("bvn_last4", sa.String(length=4), nullable=False),
        sa.Column("bank_name", sa.Text(), nullable=False),
        sa.Column("account_last4", sa.String(length=4), nullable=False),
        sa.Column(
            "stage",
            sa.Enum(
                "signed_up",
                "documents_submitted",
                "checks_in_progress",
                "bank_linked",
                "profile_ready",
                name="stage",
            ),
            nullable=False,
        ),
        sa.Column("credit_score", sa.SmallInteger(), nullable=True),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_bank_sync_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "account_last4 ~ '^[0-9]{4}$'", name=op.f("ck_businesses_account_last4_digits")
        ),
        sa.CheckConstraint("bvn_last4 ~ '^[0-9]{4}$'", name=op.f("ck_businesses_bvn_last4_digits")),
        sa.CheckConstraint(
            "credit_score BETWEEN 300 AND 850", name=op.f("ck_businesses_credit_score_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_businesses")),
        sa.UniqueConstraint("cac_number", name=op.f("uq_businesses_cac_number")),
    )
    op.create_index("ix_businesses_created_at", "businesses", ["created_at"], unique=False)
    op.create_index("ix_businesses_credit_score", "businesses", ["credit_score"], unique=False)
    op.create_index(
        "ix_businesses_last_bank_sync_at", "businesses", ["last_bank_sync_at"], unique=False
    )
    op.create_index("ix_businesses_sector", "businesses", ["sector"], unique=False)
    op.create_index("ix_businesses_stage", "businesses", ["stage"], unique=False)
    for column in ("name", "director_name"):
        op.create_index(
            f"ix_businesses_{column}_trgm",
            "businesses",
            [column],
            postgresql_using="gin",
            postgresql_ops={column: "gin_trgm_ops"},
        )
    op.create_table(
        "provider_pings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("bvn", "cac", "tin", "open_banking", name="provider"),
            nullable=False,
        ),
        sa.Column("status", sa.Enum("up", "slow", "down", name="ping_status"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_pings")),
    )
    op.create_index(
        "ix_provider_pings_provider_checked_at",
        "provider_pings",
        ["provider", sa.literal_column("checked_at DESC")],
        unique=False,
    )
    op.create_table(
        "staff_users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Enum("ops_admin", "analyst", "viewer", name="role"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_users")),
        sa.UniqueConstraint("email", name=op.f("uq_staff_users_email")),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["staff_users.id"], name=op.f("fk_audit_log_actor_id_staff_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        "ix_audit_log_target",
        "audit_log",
        ["target_type", "target_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.SmallInteger(), nullable=True),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["staff_users.id"], name=op.f("fk_idempotency_keys_actor_id_staff_users")
        ),
        sa.PrimaryKeyConstraint("key", "actor_id", name=op.f("pk_idempotency_keys")),
    )
    op.create_table(
        "verification_checks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type", sa.Enum("cac", "tin", "bvn", "bank_link", name="check_type"), nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "passed", "failed", name="check_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempts >= 0", name=op.f("ck_verification_checks_attempts_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_verification_checks_business_id_businesses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_checks")),
        sa.UniqueConstraint(
            "business_id", "type", name=op.f("uq_verification_checks_business_id_type")
        ),
    )
    op.create_index(
        "ix_verification_checks_failed",
        "verification_checks",
        ["type"],
        unique=False,
        postgresql_where=sa.text("status = 'failed'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_verification_checks_failed",
        table_name="verification_checks",
        postgresql_where=sa.text("status = 'failed'"),
    )
    op.drop_table("verification_checks")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_audit_log_target", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("staff_users")
    op.drop_index("ix_provider_pings_provider_checked_at", table_name="provider_pings")
    op.drop_table("provider_pings")
    op.drop_index("ix_businesses_director_name_trgm", table_name="businesses")
    op.drop_index("ix_businesses_name_trgm", table_name="businesses")
    op.drop_index("ix_businesses_stage", table_name="businesses")
    op.drop_index("ix_businesses_sector", table_name="businesses")
    op.drop_index("ix_businesses_last_bank_sync_at", table_name="businesses")
    op.drop_index("ix_businesses_credit_score", table_name="businesses")
    op.drop_index("ix_businesses_created_at", table_name="businesses")
    op.drop_table("businesses")
    for enum_name in (
        "role",
        "stage",
        "check_type",
        "check_status",
        "sector",
        "provider",
        "ping_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
