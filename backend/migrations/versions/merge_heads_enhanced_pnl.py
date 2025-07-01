"""merge heads for enhanced P&L

Revision ID: merge_enhanced_pnl
Revises: 7ee431d863ab, 7000d7bcb1f
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_enhanced_pnl'
down_revision = ('7ee431d863ab', '7000d7bcb1f')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no schema changes needed
    pass


def downgrade():
    # This is a merge migration - no schema changes needed
    pass 