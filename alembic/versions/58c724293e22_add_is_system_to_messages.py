"""add_is_system_to_messages

Revision ID: 58c724293e22
Revises: 
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c724293e22'
down_revision: Union[str, None] = '96212d0a50d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('messages', 'is_system')
