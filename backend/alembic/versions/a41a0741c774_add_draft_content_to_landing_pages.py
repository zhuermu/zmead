"""add_draft_content_to_landing_pages

Revision ID: a41a0741c774
Revises: 005_add_message_assets_fields
Create Date: 2025-12-10 11:22:54.878740

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a41a0741c774'
down_revision: Union[str, None] = '005_add_message_assets_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add draft_content column to landing_pages
    op.add_column('landing_pages', sa.Column('draft_content', sa.Text(), nullable=True))

    # Migrate existing data: copy html_content to draft_content for existing pages
    op.execute("UPDATE landing_pages SET draft_content = html_content WHERE html_content IS NOT NULL")


def downgrade() -> None:
    op.drop_column('landing_pages', 'draft_content')
