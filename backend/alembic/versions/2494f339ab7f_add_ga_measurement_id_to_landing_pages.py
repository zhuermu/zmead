"""add_ga_measurement_id_to_landing_pages

Revision ID: 2494f339ab7f
Revises: a41a0741c774
Create Date: 2025-12-10 14:11:41.820519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2494f339ab7f'
down_revision: Union[str, None] = 'a41a0741c774'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add GA measurement ID field for analytics tracking
    op.add_column('landing_pages', sa.Column('ga_measurement_id', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('landing_pages', 'ga_measurement_id')
