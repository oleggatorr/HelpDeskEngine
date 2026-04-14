"""rename_number_to_track_id

Revision ID: 91adc9e7fda0
Revises: e22ae198c271
Create Date: 2026-04-08 14:55:09.583821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91adc9e7fda0'
down_revision: Union[str, None] = 'e22ae198c271'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Переименовываем колонку number → track_id
    op.alter_column('documents', 'number', new_column_name='track_id')
    # Изменяем тип и длину
    op.alter_column('documents', 'track_id',
                    existing_type=sa.VARCHAR(length=20),
                    type_=sa.String(length=12),
                    existing_nullable=False)
    # Переименовываем индекс
    op.drop_index(op.f('ix_documents_number'), table_name='documents')
    op.create_index(op.f('ix_documents_track_id'), 'documents', ['track_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_track_id'), table_name='documents')
    op.create_index(op.f('ix_documents_number'), 'documents', ['number'], unique=True)
    op.alter_column('documents', 'track_id',
                    existing_type=sa.String(length=12),
                    type_=sa.VARCHAR(length=20),
                    existing_nullable=False,
                    new_column_name='number')
