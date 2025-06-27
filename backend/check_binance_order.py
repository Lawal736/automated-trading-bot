import ccxt.async_support as ccxt
import asyncio
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.exchange import ExchangeConnection
from app.core.config import settings

async def check_binance_order(order_id, symbol, api_key, api_secret, is_testnet=True):
    binance = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'adjustForTimeDifference': True},
    })
    
    if is_testnet:
        binance.set_sandbox_mode(True)
    
    try:
        order = await binance.fetch_order(order_id, symbol)
        print("Raw order object:", order)
        print("Status:", order.get('status'))
        print("Filled:", order.get('filled'))
        print("Average price:", order.get('average'))
        print("Price:", order.get('price'))
        print("Cost:", order.get('cost'))
        return order
    except Exception as e:
        print("Error fetching order:", e)
        return None
    finally:
        await binance.close()

def get_exchange_connection(user_id=1, exchange_name='binance'):
    """Get exchange connection from database"""
    # Create database session
    engine = create_engine(settings.DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Get the first exchange connection for the user
        conn = session.query(ExchangeConnection).filter_by(
            user_id=user_id, 
            exchange_name=exchange_name
        ).first()
        
        if not conn:
            print(f"No exchange connection found for user {user_id} and exchange {exchange_name}")
            return None
            
        return conn
    finally:
        session.close()

if __name__ == "__main__":
    # Get exchange connection from database
    conn = get_exchange_connection()
    if not conn:
        print("No exchange connection found. Please set up an exchange connection first.")
        sys.exit(1)
    
    print(f"Using exchange connection: {conn.exchange_name}")
    print(f"Testnet mode: {conn.is_testnet}")
    print(f"API Key: {conn.api_key[:10]}...")
    
    # Get user input
    order_id = input("Enter Binance order ID: ")
    symbol = input("Enter symbol (e.g. SUI/USDT): ")
    
    # Run the check
    asyncio.run(check_binance_order(
        order_id=order_id,
        symbol=symbol,
        api_key=conn.api_key,
        api_secret=conn.api_secret,
        is_testnet=conn.is_testnet
    )) 