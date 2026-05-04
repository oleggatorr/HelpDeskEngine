"""change_permissions_to_json

Revision ID: 257cb2247f01
Revises: 3b69671e9315
Create Date: 2026-04-30 12:36:39.815634
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '257cb2247f01'
down_revision: Union[str, None] = '3b69671e9315'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ Заменяем NULL на пустой JSON-объект
    op.execute("UPDATE user_profiles SET permissions = '{}' WHERE permissions IS NULL")

    # 2️⃣ Меняем тип + ставим NOT NULL + DEFAULT на уровне БД
    op.alter_column(
        'user_profiles',
        'permissions',
        existing_type=sa.VARCHAR(length=255),
        type_=sa.JSON(),
        nullable=False,
        server_default=sa.text("'{}'"),
        # Для PostgreSQL явный каст обязателен. Для MySQL можно убрать.
        postgresql_using="permissions::json"
    )


def downgrade() -> None:
    # ⚠️ Внимание: обратный каст обрежет JSON до 255 символов!
    op.alter_column(
        'user_profiles',
        'permissions',
        existing_type=sa.JSON(),
        type_=sa.VARCHAR(length=255),
        nullable=True,
        server_default=None,
        postgresql_using="permissions::varchar"
    )