"""add_manager_fields_to_ad_accounts

Revision ID: adde7294324f
Revises: 2494f339ab7f
Create Date: 2025-12-16 15:15:28.924851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'adde7294324f'
down_revision: Union[str, None] = '2494f339ab7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add manager account fields to ad_accounts table
    op.add_column('ad_accounts', sa.Column('is_manager', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('ad_accounts', sa.Column('manager_account_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove manager account fields from ad_accounts table
    op.drop_column('ad_accounts', 'manager_account_id')
    op.drop_column('ad_accounts', 'is_manager')
