"""Add password_reset_token table for database-backed single-use reset tokens

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-01 09:15:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =====================================================================
    # PASSWORD_RESET_TOKEN TABLE
    # =====================================================================
    op.create_table(
        "password_reset_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "token_hash",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_password_reset_token_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_token"),
    )
    op.create_index(
        "ix_password_reset_token_user_id",
        "password_reset_token",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_token_token_hash",
        "password_reset_token",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_password_reset_token_expires_at",
        "password_reset_token",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_token_is_used",
        "password_reset_token",
        ["is_used"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_token_is_used", table_name="password_reset_token"
    )
    op.drop_index(
        "ix_password_reset_token_expires_at", table_name="password_reset_token"
    )
    op.drop_index(
        "ix_password_reset_token_token_hash", table_name="password_reset_token"
    )
    op.drop_index(
        "ix_password_reset_token_user_id", table_name="password_reset_token"
    )
    op.drop_table("password_reset_token")
