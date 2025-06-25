from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.schemas.exchanges import ExchangeConnectionCreate, ExchangeConnectionUpdate
from app.core.logging import get_logger
from app.trading.exchanges.factory import ExchangeFactory
from decimal import Decimal
import asyncio
from app.models.exchange import ExchangeConnection
from app.models.bot import Bot
from app.core.cache import price_cache
from datetime import datetime
from app.schemas.ticker import Ticker
from app.schemas.trade import TradeOrder, TradeResult
from app.services.bot_service import CRUDBot

logger = get_logger(__name__)


class ExchangeService:
    def __init__(self, session: Session):
        self.session = session

    async def get_exchange_client_for_user(
        self, user_id: int, exchange_name: str
    ) -> Optional[ExchangeFactory]:
        conn = (
            self.session.query(ExchangeConnection)
            .filter_by(user_id=user_id, exchange_name=exchange_name)
            .first()
        )
        if not conn:
            logger.warning(
                f"No exchange connection found for user {user_id} and exchange {exchange_name}"
            )
            return None
        return ExchangeFactory.create_exchange(
            exchange_name=conn.exchange_name,
            api_key=conn.api_key,
            api_secret=conn.api_secret,
            is_testnet=conn.is_testnet,
            password=conn.password,
        )

    async def get_user_exchanges(self, user_id: int) -> List[ExchangeConnection]:
        return self.session.query(ExchangeConnection).filter_by(user_id=user_id).all()

    async def create_exchange_connection(
        self, user_id: int, conn_in: ExchangeConnectionCreate
    ) -> ExchangeConnection:
        # Note: In a real app, credential validation should happen here before saving.
        db_obj = ExchangeConnection(
            user_id=user_id,
            exchange_name=conn_in.exchange_name,
            api_key=conn_in.api_key,
            api_secret=conn_in.api_secret,  # TODO: Encrypt this
            password=conn_in.password,
            is_testnet=conn_in.is_testnet,
        )
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        logger.info(
            f"Exchange connection created for user {user_id} on {conn_in.exchange_name}"
        )
        return db_obj

    async def delete_exchange_connection(self, user_id: int, conn_id: int):
        conn = (
            self.session.query(ExchangeConnection)
            .filter_by(id=conn_id, user_id=user_id)
            .first()
        )
        if conn:
            # This will also delete linked bots due to cascade settings in the model
            self.session.delete(conn)
            self.session.commit()
            logger.info(
                f"Exchange connection {conn_id} and linked bots deleted for user {user_id}"
            )

    async def update_exchange_connection(
        self, user_id: int, conn_id: int, conn_in: ExchangeConnectionUpdate
    ) -> ExchangeConnection:
        """Update an exchange connection"""
        conn = (
            self.session.query(ExchangeConnection)
            .filter_by(id=conn_id, user_id=user_id)
            .first()
        )
        if not conn:
            raise ValueError(f"Exchange connection {conn_id} not found for user {user_id}")
        
        # Update the connection fields
        for field, value in conn_in.model_dump(exclude_unset=True).items():
            setattr(conn, field, value)
        
        self.session.commit()
        self.session.refresh(conn)
        logger.info(f"Exchange connection {conn_id} updated for user {user_id}")
        return conn

    async def get_ticker(
        self, user_id: int, exchange_name: str, symbol: str
    ) -> Optional[Ticker]:
        exchange = await self.get_exchange_client_for_user(user_id, exchange_name)
        if not exchange:
            return None
        try:
            return await exchange.get_ticker(symbol)
        finally:
            if exchange:
                await exchange.close()

    async def get_tickers(
        self, user_id: int, exchange_name: str, symbols: List[str]
    ) -> Dict[str, Ticker]:
        exchange = await self.get_exchange_client_for_user(user_id, exchange_name)
        if not exchange:
            return {}
        try:
            return await exchange.get_tickers(symbols)
        finally:
            if exchange:
                await exchange.close()

    async def execute_trade(
        self, user_id: int, exchange_name: str, trade_order: TradeOrder
    ) -> TradeResult:
        exchange = await self.get_exchange_client_for_user(user_id, exchange_name)
        if not exchange:
            raise Exception("Exchange connection not found or failed to initialize.")

        if not exchange.api_key or not exchange.api_secret:
            logger.error(f"API credentials not found for user {user_id} on {exchange_name}.")
            raise Exception(f"API credentials are not configured for {exchange_name}.")

        try:
            logger.info(f"Executing trade for user {user_id}: {trade_order.model_dump_json()}")
            order_result = await exchange.create_order(
                symbol=trade_order.symbol,
                order_type=trade_order.order_type,
                side=trade_order.side,
                amount=trade_order.amount,
                price=trade_order.price,
            )

            # In-depth check of the result from ccxt
            order_status = order_result.status
            if not order_result.id or order_status in ['rejected', 'expired', 'canceled']:
                # Extract more details if available from the 'info' field
                error_message = f"Trade failed on exchange with status: {order_status}"
                logger.error(f"Trade failed for user {user_id}. Reason: {error_message}")
                raise Exception(error_message)

            # CCXT returns an Order object. We adapt it to our Pydantic model.
            trade_result = TradeResult(
                id=str(order_result.id),
                symbol=order_result.symbol,
                price=float(order_result.price or 0),
                amount=float(order_result.amount),
                status=order_status or "unknown",
            )
            logger.info(f"Trade executed successfully: {trade_result.model_dump_json()}")
            return trade_result
        except Exception as e:
            logger.error(f"Trade execution failed for user {user_id}: {e}", exc_info=True)
            raise e
        finally:
            if exchange:
                await exchange.close()

    def get_historical_klines(
        self, 
        exchange_conn_id: int, 
        symbol: str, 
        timeframe: str = '4h',
        limit: int = 1000
    ) -> List:
        """
        Get historical kline data for backtesting.
        
        Args:
            exchange_conn_id: Exchange connection ID
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for data (1h, 4h, 1d, etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of kline data in format [timestamp, open, high, low, close, volume]
        """
        try:
            logger.info(f"[DEBUG] get_historical_klines called with symbol: {symbol}")
            # Get the exchange connection
            connection = get_connection_by_id(self.session, connection_id=exchange_conn_id)
            if not connection:
                raise Exception(f"Exchange connection {exchange_conn_id} not found")
            
            # Create exchange client
            exchange = ExchangeFactory.create_exchange(
                exchange_name=connection.exchange_name,
                api_key=connection.api_key,
                api_secret=connection.api_secret,
                is_testnet=connection.is_testnet,
                password=connection.password,
            )
            
            # Fetch historical data
            # Note: This is a synchronous wrapper around async code for simplicity
            # In production, you might want to handle this differently
            import asyncio
            
            async def fetch_klines():
                try:
                    df = await exchange.get_historical_klines(symbol, timeframe, limit)
                    # Convert DataFrame to list format expected by backtest service
                    # Format: [timestamp, open, high, low, close, volume]
                    klines = []
                    for _, row in df.iterrows():
                        klines.append([
                            int(row['timestamp'].timestamp() * 1000),  # Convert to milliseconds
                            float(row['open']),
                            float(row['high']),
                            float(row['low']),
                            float(row['close']),
                            float(row['volume'])
                        ])
                    return klines
                except Exception as e:
                    logger.error(f"Error within fetch_klines for {symbol}: {e}", exc_info=True)
                    return [] # Return empty list on failure to prevent crash
                finally:
                    await exchange.close()
            
            # Run the async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, we need to handle this differently
                    # For now, we'll use a simple approach
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_klines())
                        return future.result()
                else:
                    return asyncio.run(fetch_klines())
            except RuntimeError:
                # If no event loop is running, create one
                return asyncio.run(fetch_klines())
                
        except Exception as e:
            logger.error(f"Failed to get historical klines for {symbol}: {e}", exc_info=True)
            raise




async def get_real_time_prices(exchange, currencies: List[str]) -> Dict[str, Ticker]:
    """
    Fetches real-time prices for a list of currencies against USDT.
    It attempts to fetch all tickers in a single batch, with a fallback to individual fetching.
    """
    prices: Dict[str, Ticker] = {}
    
    # Handle USDT separately as it's the quote currency
    if "USDT" in currencies:
        prices["USDT"] = Ticker(symbol="USDT/USDT", last_price=Decimal("1.0"), timestamp=datetime.utcnow())
        currencies_to_fetch = [c for c in currencies if c != "USDT"]
    else:
        currencies_to_fetch = currencies

    symbols = [f"{currency}/USDT" for currency in currencies_to_fetch]
    
    if not symbols:
        return prices

    try:
        # Attempt to fetch all tickers in one batch.
        all_tickers = await exchange.get_tickers(symbols)
        for symbol, ticker_object in all_tickers.items():
            currency = symbol.split('/')[0]
            prices[currency] = ticker_object
        logger.info(f"Successfully fetched {len(all_tickers)} tickers in a single batch.")

    except Exception as e:
        logger.error(f"Failed to fetch batch tickers: {e}. Falling back to individual fetching.")
        # Fallback to fetching one by one if the batch request fails
        for currency in currencies_to_fetch:
            try:
                symbol = f"{currency}/USDT"
                ticker_object = await exchange.get_ticker(symbol)
                if ticker_object:
                    prices[currency] = ticker_object
                else:
                    logger.warning(f"No price data available for individual symbol {symbol}")
            except Exception as e_ind:
                logger.warning(f"Could not fetch individual price for {currency}/USDT: {e_ind}")

    if prices:
        # Cache the fetched prices. The key for the cache should be the full symbol.
        prices_for_cache = {ticker.symbol: ticker.model_dump() for ticker in prices.values() if isinstance(ticker, Ticker)}
        price_cache.update_prices(prices_for_cache)
            
    return prices


def get_total_balance(db: Session, *, user_id: int) -> dict:
    """
    Fetches the total balance from all connected exchanges for a user,
    aggregates all assets, and converts them to a total USD value.
    """
    # This dictionary will dynamically store all currencies and their aggregated balances.
    total_balances = {}
    total_usd_value = Decimal(0)

    async def fetch_balances():
        nonlocal total_usd_value
        connections = get_connections_by_user_id(db=db, user_id=user_id)
        
        for conn in connections:
            try:
                # We can reuse the same logic for any exchange that follows the base interface
                exchange = ExchangeFactory.create_exchange(
                    exchange_name=conn.exchange_name,
                    api_key=conn.api_key,
                    api_secret=conn.api_secret,
                    is_testnet=conn.is_testnet,
                    password=conn.password, # For exchanges like KuCoin
                )

                # Fetch both spot and futures balances
                spot_balances = await exchange.get_balance()
                # Gracefully handle exchanges that may not have a futures balance method
                futures_balances = []
                if hasattr(exchange, 'get_futures_balance'):
                    futures_balances = await exchange.get_futures_balance()
                
                # Combine all balances
                all_balances = spot_balances + futures_balances
                if not all_balances:
                    continue

                # Aggregate balances by currency
                aggregated_balances: Dict[str, Decimal] = {}
                for balance in all_balances:
                    currency = balance.currency
                    aggregated_balances.setdefault(currency, Decimal(0))
                    aggregated_balances[currency] += balance.total

                # Update the master balance dictionary
                for currency, total in aggregated_balances.items():
                    total_balances.setdefault(currency, Decimal(0))
                    total_balances[currency] += total

                # Fetch real-time prices for all held currencies
                currencies_to_price = list(aggregated_balances.keys())
                prices = await get_real_time_prices(exchange, currencies_to_price)
                
                # Calculate total USD value for this connection
                for currency, total in aggregated_balances.items():
                    if currency == "USDT":
                        total_usd_value += total
                    elif currency in prices and prices[currency] and prices[currency].last_price:
                        total_usd_value += total * prices[currency].last_price
                    else:
                        logger.warning(f"No price available for {currency} on {conn.exchange_name}, excluding from total value.")

                await exchange.close()
                logger.info(f"Successfully processed balances from {conn.exchange_name} for user {user_id}")

            except Exception as e:
                logger.error(f"Failed to fetch balance from {conn.exchange_name} for user {user_id}: {e}", exc_info=True)
                continue

    # Using asyncio.run is a modern and safer way to run an async function from a sync context.
    try:
        asyncio.run(fetch_balances())
    except RuntimeError:
        # If an event loop is already running (e.g., in a notebook), use a different approach.
        loop = asyncio.get_event_loop()
        loop.run_until_complete(fetch_balances())

    # Add the final total USD value to the balances dictionary for the response.
    total_balances["total_usd_value"] = total_usd_value
    
    # Convert all Decimal values to float for JSON serialization
    return {k: float(v) for k, v in total_balances.items()}


def get_connection_by_id(
    db: Session, *, connection_id: int
) -> ExchangeConnection:
    """
    Get a specific exchange connection by ID.
    """
    try:
        connection = db.query(ExchangeConnection).filter(ExchangeConnection.id == connection_id).first()
        return connection
    except Exception as e:
        logger.error(f"Error fetching exchange connection by ID: {str(e)}")
        raise


def delete_connection(
    db: Session, *, connection_id: int
) -> None:
    """
    Delete an exchange connection by ID.
    """
    try:
        connection = db.query(ExchangeConnection).filter(ExchangeConnection.id == connection_id).first()
        if not connection:
            logger.warning(f"Exchange connection {connection_id} not found for deletion")
            return
        
        # Check if there are any bots linked to this connection
        linked_bots = db.query(Bot).filter(Bot.exchange_connection_id == connection_id).all()
        
        if linked_bots:
            logger.warning(f"Found {len(linked_bots)} bots linked to exchange connection {connection_id}. They will be deleted.")
        
        # Delete the exchange connection (cascade will handle bot deletion)
        db.delete(connection)
        db.commit()
        logger.info(f"Exchange connection {connection_id} and {len(linked_bots)} linked bots deleted successfully")
        
    except Exception as e:
        logger.error(f"Error deleting exchange connection: {str(e)}")
        db.rollback()
        raise


def get_connections_by_user_id(
    db: Session, *, user_id: int
) -> List[ExchangeConnection]:
    """
    Get all exchange connections for a specific user.
    """
    try:
        connections = db.query(ExchangeConnection).filter(ExchangeConnection.user_id == user_id).all()
        logger.info(f"Retrieved {len(connections)} exchange connections", user_id=user_id)
        return connections
    except Exception as e:
        logger.error(f"Error fetching exchange connections: {str(e)}")
        raise 