"""add_price_column_to_cassava_trend_data

Revision ID: 60557ca5ea95
Revises: add_cassava_trend_data
Create Date: 2025-06-28 14:09:30.087929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60557ca5ea95'
down_revision: Union[str, Sequence[str], None] = 'add_cassava_trend_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('cassava_trend_data', sa.Column('price', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cassava_trend_data', 'price')
