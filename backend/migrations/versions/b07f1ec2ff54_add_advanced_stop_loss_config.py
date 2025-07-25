"""add_advanced_stop_loss_config

Revision ID: b07f1ec2ff54
Revises: b21e73b30f91
Create Date: 2025-06-22 11:04:48.848320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b07f1ec2ff54'
down_revision: Union[str, Sequence[str], None] = 'b21e73b30f91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('bots', sa.Column('stop_loss_type', sa.String(length=50), nullable=True))
    op.add_column('bots', sa.Column('stop_loss_percentage', sa.Float(), nullable=True))
    op.add_column('bots', sa.Column('stop_loss_timeframe', sa.String(length=10), nullable=True))
    op.add_column('bots', sa.Column('stop_loss_ema_period', sa.Integer(), nullable=True))
    op.add_column('bots', sa.Column('stop_loss_atr_period', sa.Integer(), nullable=True))
    op.add_column('bots', sa.Column('stop_loss_atr_multiplier', sa.Float(), nullable=True))
    op.add_column('bots', sa.Column('stop_loss_support_lookback', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('bots', 'stop_loss_support_lookback')
    op.drop_column('bots', 'stop_loss_atr_multiplier')
    op.drop_column('bots', 'stop_loss_atr_period')
    op.drop_column('bots', 'stop_loss_ema_period')
    op.drop_column('bots', 'stop_loss_timeframe')
    op.drop_column('bots', 'stop_loss_percentage')
    op.drop_column('bots', 'stop_loss_type')
    # ### end Alembic commands ###
