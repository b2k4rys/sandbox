"""add running to celerystatuses enum

Revision ID: 68a96284d13c
Revises: 8ed11697f9fa
Create Date: 2026-06-15 20:12:51.308347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68a96284d13c'
down_revision: Union[str, Sequence[str], None] = '8ed11697f9fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE celerystatuses ADD VALUE IF NOT EXISTS 'RUNNING'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
