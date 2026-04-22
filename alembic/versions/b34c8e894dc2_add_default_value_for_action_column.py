"""add default value for action column

Revision ID: b34c8e894dc2
Revises: 340b6884fdac
Create Date: 2026-04-16 11:40:18.303019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b34c8e894dc2'
down_revision: Union[str, None] = '340b6884fdac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# В upgrade():
def upgrade():
    # Сначала заполняем существующие NULL-значения (если есть)
    op.execute("""
        UPDATE problem_registrations 
        SET action = 'UNDEFINED'::problem_action_enum 
        WHERE action IS NULL
    """)
    
    # Добавляем DEFAULT для новых записей
    op.alter_column(
        'problem_registrations',
        'action',
        server_default='UNDEFINED',  # ← Значение по умолчанию
        existing_type=sa.Enum('UNDEFINED', 'REJECTED', 'CLOSED', 'ASSIGN_EXEC', name='problem_action_enum'),
        existing_nullable=False  # Оставляем NOT NULL
    )

# В downgrade():
def downgrade():
    op.alter_column(
        'problem_registrations',
        'action',
        server_default=None,
        existing_type=sa.Enum('UNDEFINED', 'REJECTED', 'CLOSED', 'ASSIGN_EXEC', name='problem_action_enum'),
        existing_nullable=False
    )
