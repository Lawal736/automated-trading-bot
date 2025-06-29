import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.trading import Trade
from app.models.exchange import ExchangeConnection
from app.models.user import User
from app.services.exchange_service import ExchangeService
from app.services.activity_service import ActivityService, ActivityCreate
from app.services.stop_loss_timeout_handler import create_stop_loss_safe
from app.trading.exchanges.factory import ExchangeFactory
from app.core.config import settings
import logging

ORDER_ID = '11112713615'  # The order ID for Trade ID 29

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_stop_loss")

def get_db():
    engine = create_engine(settings.DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

async def main():
    session = get_db()
    try:
        # Find the trade by exchange_order_id
        trade = session.query(Trade).filter(Trade.exchange_order_id == ORDER_ID).first()
        if not trade:
            logger.error(f"Trade with exchange_order_id {ORDER_ID} not found.")
            return
        logger.info(f"Found trade: {trade.id}, symbol: {trade.symbol}, user_id: {trade.user_id}, amount: {trade.quantity}, executed_price: {trade.executed_price}, stop_loss: {trade.stop_loss}")

        # Get exchange connection
        exchange_conn = session.query(ExchangeConnection).filter_by(id=trade.exchange_connection_id).first()
        if not exchange_conn:
            logger.error(f"Exchange connection {trade.exchange_connection_id} not found.")
            return

        # Get the user
        user = session.query(User).filter(User.id == trade.user_id).first()
        if not user:
            logger.error(f"User {trade.user_id} not found.")
            return

        # Use user's stored stop loss if available, otherwise calculate default
        if trade.stop_loss is not None:
            stop_loss_price = trade.stop_loss
            logger.info(f"Using user's stored stop loss: {stop_loss_price}")
        else:
            # Fallback to calculated stop loss
            if trade.side == 'buy':
                stop_loss_price = trade.executed_price * 0.98  # 2% below executed price for buy orders
            else:
                stop_loss_price = trade.executed_price * 1.02  # 2% above executed price for sell orders
            logger.info(f"Using calculated stop loss: {stop_loss_price}")

        # Create a mock trade order object for the stop loss
        class MockTradeOrder:
            def __init__(self, symbol, side, amount, stop_loss):
                self.symbol = symbol
                self.side = side
                self.amount = amount
                self.stop_loss = stop_loss

        # For buy orders: stop loss is sell order (stop below executed price)
        # For sell orders: stop loss is buy order (stop above executed price)
        side = 'sell' if trade.side == 'buy' else 'buy'
        
        trade_order = MockTradeOrder(
            symbol=trade.symbol,
            side=side,
            amount=trade.quantity,
            stop_loss=stop_loss_price
        )
        
        logger.info(f"Attempting to place stop loss: symbol={trade.symbol}, side={side}, amount={trade.quantity}, stop_loss={stop_loss_price}")

        # Create exchange instance
        exchange = ExchangeFactory.create_exchange(
            exchange_name=exchange_conn.exchange_name,
            api_key=exchange_conn.api_key,
            api_secret=exchange_conn.api_secret,
            is_testnet=exchange_conn.is_testnet
        )

        # Create activity service
        activity_service = ActivityService(ActivityCreate)

        # Use the robust timeout handler to create stop loss order
        stop_loss_order = await create_stop_loss_safe(
            trade_order, 
            trade.user_id, 
            exchange_conn, 
            user, 
            activity_service, 
            exchange, 
            session
        )
        
        if stop_loss_order:
            logger.info(f"Stop loss order placed successfully using timeout handler: {stop_loss_order}")
        else:
            logger.error("Stop loss order creation failed using timeout handler")
            
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main()) 