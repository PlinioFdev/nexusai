"""add api_key to tenants

Revision ID: a1b2c3d4e5f6
Revises: 26c9c1fc3982
Create Date: 2026-05-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "26c9c1fc3982"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("api_key", sa.String(length=64), nullable=True),
    )
    op.create_index(op.f("ix_tenants_api_key"), "tenants", ["api_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_tenants_api_key"), table_name="tenants")
    op.drop_column("tenants", "api_key")
