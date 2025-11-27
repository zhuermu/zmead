"""Add credit config logs table

Revision ID: 002_add_credit_config_logs
Revises: 001_initial_schema
Create Date: 2024-11-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_credit_config_logs'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create credit_config_logs table."""
    op.create_table(
        'credit_config_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('config_id', sa.BigInteger(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=False),
        sa.Column('changed_by', sa.String(length=255), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_config_logs_config_id', 'credit_config_logs', ['config_id'])
    op.create_index('idx_config_logs_changed_at', 'credit_config_logs', ['changed_at'])
    op.create_index('idx_config_logs_field', 'credit_config_logs', ['field_name'])


def downgrade() -> None:
    """Drop credit_config_logs table."""
    op.drop_index('idx_config_logs_field', table_name='credit_config_logs')
    op.drop_index('idx_config_logs_changed_at', table_name='credit_config_logs')
    op.drop_index('idx_config_logs_config_id', table_name='credit_config_logs')
    op.drop_table('credit_config_logs')
