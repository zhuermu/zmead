"""Add conversations and messages tables for AI chat.

Revision ID: 003_add_conversations_messages
Revises: 002_add_credit_config_logs
Create Date: 2024-11-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '003_add_conversations_messages'
down_revision: Union[str, None] = '002_add_credit_config_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('current_intent', sa.String(100), nullable=True),
        sa.Column('context_data', mysql.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'], unique=False)
    op.create_index('ix_conversations_session_id', 'conversations', ['session_id'], unique=True)
    op.create_index(
        'ix_conversations_user_updated', 'conversations', ['user_id', 'updated_at'], unique=False
    )
    op.create_index(
        'ix_conversations_user_last_message', 'conversations',
        ['user_id', 'last_message_at'], unique=False
    )

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', mysql.JSON(), nullable=True),
        sa.Column('tool_call_id', sa.String(255), nullable=True),
        sa.Column('message_metadata', mysql.JSON(), nullable=False),
        sa.Column('input_tokens', sa.BigInteger(), nullable=True),
        sa.Column('output_tokens', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'], unique=False)
    op.create_index(
        'ix_messages_conversation_created', 'messages',
        ['conversation_id', 'created_at'], unique=False
    )


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('conversations')
