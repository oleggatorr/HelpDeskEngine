"""More letters fo MIME

Revision ID: 340b6884fdac
Revises: b5407f495b37
Create Date: 2026-04-16 08:52:14.534542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '340b6884fdac'
down_revision: Union[str, None] = 'b5407f495b37'
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
