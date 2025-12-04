"""Add client_message_id to messages table.

Revision ID: 004_add_client_message_id
Revises: 003_add_conversations_messages
Create Date: 2024-12-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_client_message_id'
down_revision = '003_add_conversations_messages'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add client_message_id column to messages table
    op.add_column(
        'messages',
        sa.Column('client_message_id', sa.String(255), nullable=True)
    )
    op.create_index(
        'ix_messages_client_message_id',
        'messages',
        ['client_message_id']
    )


def downgrade() -> None:
    op.drop_index('ix_messages_client_message_id', table_name='messages')
    op.drop_column('messages', 'client_message_id')
