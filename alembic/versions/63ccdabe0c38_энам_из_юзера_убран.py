"""энам из юзера убран

Revision ID: 63ccdabe0c38
Revises: c19488d86f01
Create Date: 2026-04-27 10:11:23.744609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '63ccdabe0c38'
down_revision: Union[str, None] = 'c19488d86f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('corrections', 'status',
               existing_type=postgresql.ENUM('planned', 'in_progress', 'completed', 'verified', 'rejected', name='correctionstatus'),
               type_=sa.String(length=20),
               existing_nullable=False,
               existing_server_default=sa.text("'planned'::correctionstatus"),
               postgresql_using="status::text")  # ✅ Приводим ENUM к тексту

def downgrade() -> None:
    op.alter_column('corrections', 'status',
               existing_type=sa.String(length=20),
               type_=postgresql.ENUM('planned', 'in_progress', 'completed', 'verified', 'rejected', name='correctionstatus'),
               existing_nullable=False,
               existing_server_default=sa.text("'planned'::correctionstatus"),
               postgresql_using="status::correctionstatus")
