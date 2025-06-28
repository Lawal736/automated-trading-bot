import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.trading import Trade
from app.models.exchange import ExchangeConnection
from app.services.exchange_service import ExchangeService
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

        # Create exchange instance
        exchange = ExchangeFactory.create_exchange(
            exchange_name=exchange_conn.exchange_name,
            api_key=exchange_conn.api_key,
            api_secret=exchange_conn.api_secret,
            is_testnet=exchange_conn.is_testnet
        )

        # Load markets and get precision/limits
        await exchange.client.load_markets()
        market = exchange.client.market(trade.symbol)
        price_precision = market['precision']['price']
        amount_precision = market['precision']['amount']
        
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

        # Apply precision to stop loss price
        stop_price = round(float(stop_loss_price), price_precision)
        rounded_quantity = round(float(trade.quantity), amount_precision)
        
        # Calculate limit price with buffer (0.1% buffer)
        # For buy orders: stop loss is sell order (stop below executed price)
        # For sell orders: stop loss is buy order (stop above executed price)
        side = 'sell' if trade.side == 'buy' else 'buy'
        
        if side == 'sell':
            # Selling to stop loss - limit price should be below stop price
            limit_price = round(stop_price * 0.999, price_precision)  # 0.1% below stop price
        else:
            # Buying to stop loss - limit price should be above stop price
            limit_price = round(stop_price * 1.001, price_precision)  # 0.1% above stop price
        
        logger.info(f"Precision - Price: {price_precision}, Amount: {amount_precision}")
        logger.info(f"Rounded values - Stop price: {stop_price}, Limit price: {limit_price}, Quantity: {rounded_quantity}")
        logger.info(f"Attempting to place stop loss: symbol={trade.symbol}, side={side}, amount={rounded_quantity}, stop_price={stop_price}, limit_price={limit_price}")

        order_params = {"stopPrice": stop_price, "timeInForce": "GTC"}
        order_type_variants = ["stop_loss_limit", "stop-limit", "STOP_LOSS_LIMIT"]
        stop_loss_order = None
        last_error = None
        
        for order_type in order_type_variants:
            try:
                logger.info(f"Trying order_type: {order_type}")
                stop_loss_order = await exchange.client.create_order(
                    symbol=trade.symbol,
                    type=order_type,
                    side=side,
                    amount=rounded_quantity,
                    price=limit_price,
                    params=order_params
                )
                logger.info(f"Stop loss order created: {stop_loss_order}")
                break
            except Exception as e:
                last_error = e
                logger.error(f"Failed with order_type {order_type}: {e}")
                continue
                
        if stop_loss_order is None:
            logger.error(f"All order type variants failed. Last error: {last_error}")
        else:
            logger.info(f"Stop loss order placed successfully: {stop_loss_order}")
            
    finally:
        await exchange.close()
        session.close()

if __name__ == "__main__":
    asyncio.run(main()) 