"""add_stop_loss_trade_type_to_constraint

Revision ID: ffd4564475ec
Revises: merge_enhanced_pnl
Create Date: 2025-07-01 15:51:09.493299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffd4564475ec'
down_revision: Union[str, Sequence[str], None] = 'merge_enhanced_pnl'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old constraint
    op.drop_constraint('valid_trade_type', 'trades', type_='check')
    
    # Add the new constraint with 'STOP_LOSS' included
    op.create_check_constraint(
        'valid_trade_type',
        'trades',
        "trade_type IN ('spot', 'futures', 'STOP_LOSS')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new constraint
    op.drop_constraint('valid_trade_type', 'trades', type_='check')
    
    # Restore the old constraint
    op.create_check_constraint(
        'valid_trade_type',
        'trades',
        "trade_type IN ('spot', 'futures')"
    )
