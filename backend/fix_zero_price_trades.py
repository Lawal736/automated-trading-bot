import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.trading import Trade
from app.models.exchange import ExchangeConnection
from app.services.exchange_service import ExchangeService
from app.trading.exchanges.factory import ExchangeFactory
from app.core.config import settings

def get_exchange_for_trade(db: Session, trade: Trade):
    """Get exchange instance for a trade"""
    exchange_conn = db.query(ExchangeConnection).filter_by(id=trade.exchange_connection_id).first()
    if not exchange_conn:
        return None
    
    return ExchangeFactory.create_exchange(
        exchange_name=exchange_conn.exchange_name,
        api_key=exchange_conn.api_key,
        api_secret=exchange_conn.api_secret,
        is_testnet=exchange_conn.is_testnet
    )

async def fix_zero_price_trades():
    """Fix trades with zero executed prices by fetching the actual executed price from Binance"""
    engine = create_engine(settings.DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Get all trades with zero executed price
        zero_price_trades = session.query(Trade).filter(
            Trade.executed_price == 0,
        ).all()
        
        print(f"Found {len(zero_price_trades)} trades with zero executed price")
        
        for trade in zero_price_trades:
            print(f"\nProcessing trade {trade.id}: {trade.symbol} {trade.side} {trade.quantity}")
            
            # Get exchange connection
            exchange_conn = session.query(ExchangeConnection).filter_by(id=trade.exchange_connection_id).first()
            if not exchange_conn:
                print(f"No exchange connection found for trade {trade.id}")
                continue
            
            # Create exchange instance
            exchange = ExchangeFactory.create_exchange(
                exchange_name=exchange_conn.exchange_name,
                api_key=exchange_conn.api_key,
                api_secret=exchange_conn.api_secret,
                is_testnet=exchange_conn.is_testnet
            )
            
            try:
                # Get the raw order from exchange
                raw_order = await exchange.client.fetch_order(trade.exchange_order_id, trade.symbol)
                print(f"Raw order response: {raw_order}")
                
                # Use 'average' field as the primary executed price
                executed_price = raw_order.get('average')
                if executed_price:
                    print(f"Using 'average' field: {executed_price}")
                else:
                    # Fallback to other fields
                    executed_price = (
                        raw_order.get('price') or
                        raw_order.get('executed_price') or
                        0
                    )
                    print(f"Using fallback price: {executed_price}")
                
                # If still no price, try trade history
                if not executed_price or executed_price == 0:
                    trades = await exchange.client.fetch_my_trades(trade.symbol)
                    for t in trades:
                        if str(t.get('order')) == str(trade.exchange_order_id):
                            executed_price = float(t.get('price', 0))
                            print(f"Matched executed price from trade history for trade {trade.id}: {executed_price}")
                            break
                
                # Update the trade if we found a valid price
                if executed_price and executed_price != 0:
                    print(f"Updating trade {trade.id} with executed price {executed_price}")
                    trade.executed_price = executed_price
                    session.commit()
                else:
                    print(f"Could not find valid executed price for trade {trade.id}")
                    
            except Exception as e:
                print(f"Error processing trade {trade.id}: {e}")
            finally:
                await exchange.close()
        
        print(f"\nFixed {len(zero_price_trades)} trades")
        
    finally:
        session.close()

def main():
    """Main function to run the fix"""
    asyncio.run(fix_zero_price_trades())

if __name__ == "__main__":
    main() 