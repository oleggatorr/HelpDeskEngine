"""add_qe_role_and_migrate_operator

Revision ID: 2853cfafd019
Revises: b34c8e894dc2
Create Date: 2026-04-16 15:24:40.657241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2853cfafd019'
down_revision: Union[str, None] = 'b34c8e894dc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Проверьте точное имя ENUM-типа в вашей БД:
# SELECT typname FROM pg_type WHERE typname LIKE '%userrole%';
# Обычно SQLAlchemy называет его `userrole` (имя класса в нижнем регистре)
ENUM_TYPE_NAME = "userrole"

def upgrade():
    # 1️⃣ Добавляем новое значение 'qe' в ENUM-тип
    op.execute(f"ALTER TYPE {ENUM_TYPE_NAME} ADD VALUE 'qe'")
    
    # 2️⃣ ⚠️ ВАЖНО: Фиксируем транзакцию, чтобы новое значение стало видимым
    # Это необходимо для PostgreSQL 12+, где ALTER TYPE ... ADD VALUE работает в отдельной транзакции
    op.execute("COMMIT")
    
    # 3️⃣ Теперь безопасно обновляем данные: переносим 'operator' → 'qe'
    op.execute("UPDATE user_profiles SET role = 'qe' WHERE role = 'operator'")

def downgrade():
    # Возвращаем данные обратно
    op.execute("UPDATE user_profiles SET role = 'operator' WHERE role = 'qe'")
    # Значение 'qe' останется в типе, но приложение его больше не увидит