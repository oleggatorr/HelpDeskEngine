"""add_user_role_enum

Revision ID: e22ae198c271
Revises: b1744c7adf37
Create Date: 2026-04-08 11:13:09.539354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e22ae198c271'
down_revision: Union[str, None] = 'b1744c7adf37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём enum type в PostgreSQL (нижний регистр, как в UserRole)
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'operator', 'user')")
    # Конвертируем существующие данные в нижний регистр
    op.execute("UPDATE user_profiles SET role = LOWER(role)")
    op.alter_column('user_profiles', 'role',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Enum('admin', 'operator', 'user', name='userrole'),
               existing_nullable=True,
               postgresql_using="LOWER(role)::userrole")


def downgrade() -> None:
    op.alter_column('user_profiles', 'role',
               existing_type=sa.Enum('admin', 'operator', 'user', name='userrole'),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)
    op.execute("DROP TYPE userrole")
