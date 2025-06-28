"""Add cassava trend data table

Revision ID: add_cassava_trend_data
Revises: 591a6d0e1cb0
Create Date: 2024-06-28 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_cassava_trend_data'
down_revision = '591a6d0e1cb0'
branch_labels = None
depends_on = None


def upgrade():
    # Create cassava_trend_data table
    op.create_table('cassava_trend_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('ema_10', sa.Float(), nullable=False),
        sa.Column('ema_8', sa.Float(), nullable=False),
        sa.Column('ema_20', sa.Float(), nullable=False),
        sa.Column('ema_15', sa.Float(), nullable=False),
        sa.Column('ema_25', sa.Float(), nullable=False),
        sa.Column('ema_5', sa.Float(), nullable=False),
        sa.Column('di_plus', sa.Float(), nullable=False),
        sa.Column('top_fractal', sa.Float(), nullable=True),
        sa.Column('trading_condition', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_cassava_trend_data_date'), 'cassava_trend_data', ['date'], unique=False)
    op.create_index(op.f('ix_cassava_trend_data_symbol'), 'cassava_trend_data', ['symbol'], unique=False)
    
    # Create unique constraint for date + symbol
    op.create_unique_constraint('unique_date_symbol', 'cassava_trend_data', ['date', 'symbol'])
    
    # Create check constraint for trading_condition
    op.create_check_constraint('valid_trading_condition', 'cassava_trend_data', 
                              "trading_condition IN ('BUY', 'SHORT', 'HOLD')")


def downgrade():
    # Drop constraints and indexes
    op.drop_constraint('valid_trading_condition', 'cassava_trend_data', type_='check')
    op.drop_constraint('unique_date_symbol', 'cassava_trend_data', type_='unique')
    op.drop_index(op.f('ix_cassava_trend_data_symbol'), table_name='cassava_trend_data')
    op.drop_index(op.f('ix_cassava_trend_data_date'), table_name='cassava_trend_data')
    
    # Drop table
    op.drop_table('cassava_trend_data')
    
    # Drop column
    op.drop_column('cassava_trend_data', 'price') 