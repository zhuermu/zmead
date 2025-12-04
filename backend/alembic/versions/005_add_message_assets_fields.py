"""Add process_info, generated_assets, and attachments to messages table.

Revision ID: 005_add_message_assets_fields
Revises: 004_add_client_message_id
Create Date: 2024-12-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '005_add_message_assets_fields'
down_revision = '004_add_client_message_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to messages table
    op.add_column('messages', sa.Column('process_info', sa.Text(), nullable=True))
    op.add_column('messages', sa.Column('generated_assets', mysql.JSON(), nullable=True))
    op.add_column('messages', sa.Column('attachments', mysql.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'attachments')
    op.drop_column('messages', 'generated_assets')
    op.drop_column('messages', 'process_info')
