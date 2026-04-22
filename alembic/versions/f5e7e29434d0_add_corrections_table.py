"""add corrections table

Revision ID: f5e7e29434d0
Revises: 63cb953bddc3
Create Date: 2026-04-21 15:23:58.169357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f5e7e29434d0'
down_revision: Union[str, None] = '63cb953bddc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'corrections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('problem_registration_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('corrective_action', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('planned', 'in_progress', 'completed', 'verified', 'rejected', name='correctionstatus'), nullable=False),
        sa.Column('planned_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('completed_by', sa.Integer(), nullable=True),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['problem_registration_id'], ['problem_registrations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['completed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_corrections_id'), 'corrections', ['id'], unique=False)
    op.create_index(op.f('ix_corrections_document_id'), 'corrections', ['document_id'], unique=False)
    op.create_index(op.f('ix_corrections_problem_registration_id'), 'corrections', ['problem_registration_id'], unique=False)
    op.create_index(op.f('ix_corrections_created_by'), 'corrections', ['created_by'], unique=False)
