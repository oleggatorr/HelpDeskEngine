"""More letters fo MIME

Revision ID: b5407f495b37
Revises: 34f56d00b896
Create Date: 2026-04-16 08:45:43.539601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5407f495b37'
down_revision: Union[str, None] = '34f56d00b896'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        'document_attachments',
        'file_type',
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),  # или sa.Text()
        existing_nullable=True
    )

def downgrade():
    op.alter_column(
        'document_attachments',
        'file_type',
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=True
    )
