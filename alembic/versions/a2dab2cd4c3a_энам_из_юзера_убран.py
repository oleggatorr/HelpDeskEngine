"""энам из юзера убран

Revision ID: a2dab2cd4c3a
Revises: 9fd629d972c7
Create Date: 2026-04-27 09:00:03.345739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a2dab2cd4c3a'
down_revision: Union[str, None] = '9fd629d972c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Меняем тип с ENUM на VARCHAR, явно указывая кастинг
    op.alter_column(
        'user_profiles', 'role',
        existing_type=postgresql.ENUM('admin', 'user', 'qe', 'owner', 'assignee', name='userrole'),
        type_=sa.String(20),
        nullable=False,
        postgresql_using="role::varchar"  # 🔑 Обязательно для PostgreSQL
    )
    
    # 2. Удаляем старый ENUM-тип, чтобы не загрязнять схему БД
    op.execute("DROP TYPE IF EXISTS userrole;")


def downgrade() -> None:
    # 1. Воссоздаём ENUM перед обратным изменением колонки
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user', 'qe', 'owner', 'assignee');")
    
    # 2. Возвращаем тип колонки обратно
    op.alter_column(
        'user_profiles', 'role',
        existing_type=sa.String(20),
        type_=postgresql.ENUM('admin', 'user', 'qe', 'owner', 'assignee', name='userrole'),
        nullable=False,
        postgresql_using="role::userrole"
    )
