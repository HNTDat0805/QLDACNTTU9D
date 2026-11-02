"""Add code column to service table for unique service identification

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-01 09:38:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Thêm cột code vào bảng service
    op.add_column(
        "service",
        sa.Column(
            "code",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_service_code",
        "service",
        ["code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_service_code", table_name="service")
    op.drop_column("service", "code")
