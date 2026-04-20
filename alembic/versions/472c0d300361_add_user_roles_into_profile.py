"""Add user roles into profile

Revision ID: 472c0d300361
Revises: 2853cfafd019
Create Date: 2026-04-17 10:54:15.902084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '472c0d300361'
down_revision: Union[str, None] = '2853cfafd019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # PostgreSQL требует выполнения ALTER TYPE ... ADD VALUE вне транзакции.
    # autocommit_block временно отключает транзакцию Alembic для этих команд.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE userrole ADD VALUE 'owner'"))
        op.execute(sa.text("ALTER TYPE userrole ADD VALUE 'assignee'"))
    # ### end Alembic commands ###


def downgrade() -> None:
    pass
