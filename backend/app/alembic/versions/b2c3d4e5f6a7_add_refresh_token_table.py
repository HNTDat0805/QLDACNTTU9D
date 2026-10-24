"""Add refresh_token table for JWT refresh token lifecycle and revocation

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-24 11:15:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =====================================================================
    # REFRESH_TOKEN TABLE
    # =====================================================================
    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "token_hash",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column(
            "jti",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by_jti",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_refresh_token_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_token"),
    )
    op.create_index(
        "ix_refresh_token_user_id", "refresh_token", ["user_id"], unique=False
    )
    op.create_index(
        "ix_refresh_token_token_hash", "refresh_token", ["token_hash"], unique=True
    )
    op.create_index("ix_refresh_token_jti", "refresh_token", ["jti"], unique=True)
    op.create_index(
        "ix_refresh_token_expires_at", "refresh_token", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_refresh_token_is_revoked", "refresh_token", ["is_revoked"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_token_is_revoked", table_name="refresh_token")
    op.drop_index("ix_refresh_token_expires_at", table_name="refresh_token")
    op.drop_index("ix_refresh_token_jti", table_name="refresh_token")
    op.drop_index("ix_refresh_token_token_hash", table_name="refresh_token")
    op.drop_index("ix_refresh_token_user_id", table_name="refresh_token")
    op.drop_table("refresh_token")
