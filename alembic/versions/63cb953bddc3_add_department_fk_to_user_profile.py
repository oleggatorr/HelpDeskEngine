"""add_department_fk_to_user_profile

Revision ID: 63cb953bddc3
Revises: 472c0d300361
Create Date: 2026-04-20 09:54:55.784990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '63cb953bddc3'
down_revision: Union[str, None] = '472c0d300361'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Добавляем колонку
    op.add_column('user_profiles', sa.Column('department_id', sa.Integer(), nullable=True))
    
    # 2. Создаём FK-ограничение
    op.create_foreign_key(
        None,  # Alembic сгенерирует имя автоматически
        'user_profiles', 'departments',
        ['department_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade() -> None:
    # 1. Сначала удаляем FK
    op.drop_constraint(None, 'user_profiles', type_='foreignkey')
    # 2. Затем удаляем колонку
    op.drop_column('user_profiles', 'department_id')