import asyncio
from decimal import Decimal
import os
import sys

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


from app.trading.exchanges.binance import BinanceExchange
from app.trading.exchanges.base import Ticker, OrderBook


async def run_tests():
    """Runs all tests for the BinanceExchange public endpoints."""
    print("--- Running Binance Exchange Tests ---")
    # Instantiate without API keys for public endpoint testing
    exchange = BinanceExchange(is_testnet=True, api_key=None, api_secret=None)
    
    try:
        # Test 1: Connection
        print("1. Testing connection...")
        connected = await exchange.test_connection()
        assert connected, "Connection test failed."
        print("   ✅ Connection successful.")

        # Test 2: Get Exchange Info
        print("2. Testing get_exchange_info...")
        info = await exchange.get_exchange_info()
        assert isinstance(info, dict) and 'spot' in info and 'futures' in info
        print("   ✅ Exchange info fetched successfully.")

        # Test 3: Get Symbols
        print("3. Testing get_symbols...")
        symbols = await exchange.get_symbols()
        assert isinstance(symbols, list) and 'BTC/USDT' in symbols
        print(f"   ✅ Fetched {len(symbols)} symbols.")

        # Test 4: Get Ticker
        print("4. Testing get_ticker...")
        ticker = await exchange.get_ticker('BTC/USDT')
        assert isinstance(ticker, Ticker) and ticker.last_price > 0
        print(f"   ✅ Fetched Ticker for BTC/USDT: ${ticker.last_price}")

        # Test 5: Get Order Book
        print("5. Testing get_order_book...")
        order_book = await exchange.get_order_book('BTC/USDT', limit=5)
        assert isinstance(order_book, OrderBook) and len(order_book.bids) == 5
        print("   ✅ Fetched Order Book for BTC/USDT.")

    except Exception as e:
        print(f"❌ A test failed: {e}", exc_info=True)
    finally:
        await exchange.close()
        print("--- Tests complete ---")


if __name__ == "__main__":
    # This setup is necessary to ensure the app modules can be found when run directly.
    from app.core.logging import setup_logging
    setup_logging()
    asyncio.run(run_tests())
