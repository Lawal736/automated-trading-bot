from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.schemas.exchanges import ExchangeConnectionCreate, ExchangeConnectionUpdate
from app.core.logging import get_logger
from app.trading.exchanges.factory import ExchangeFactory
from decimal import Decimal
import asyncio
from app.models.exchange import ExchangeConnection
from app.models.bot import Bot
from app.models.trading import Trade, OrderStatus, OrderType, Position
from app.core.cache import price_cache
from datetime import datetime
from app.schemas.ticker import Ticker
from app.schemas.trade import TradeOrder, TradeResult
from app.services.bot_service import CRUDBot
from app.trading.exchanges.base import OrderType

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
        """
        Execute a trade with the correct flow: Database First → Exchange → Update Database
        """
        exchange = await self.get_exchange_client_for_user(user_id, exchange_name)
        if not exchange:
            raise Exception("Exchange connection not found or failed to initialize.")

        if not exchange.api_key or not exchange.api_secret:
            logger.error(f"API credentials not found for user {user_id} on {exchange_name}.")
            raise Exception(f"API credentials are not configured for {exchange_name}.")

        # Get the exchange connection for this user and exchange
        exchange_conn = (
            self.session.query(ExchangeConnection)
            .filter_by(user_id=user_id, exchange_name=exchange_name)
            .first()
        )
        
        if not exchange_conn:
            raise Exception(f"Exchange connection not found for user {user_id} and exchange {exchange_name}")

        # STEP 1: Create pending trade record in database FIRST
        try:
            pending_trade = Trade(
                user_id=user_id,
                exchange_connection_id=exchange_conn.id,
                symbol=trade_order.symbol,
                trade_type=trade_order.trade_type,  # Use actual trade type from order
                order_type=trade_order.order_type,
                side=trade_order.side,
                quantity=trade_order.amount,
                price=float(trade_order.price) if trade_order.price else 0.0,
                executed_price=0.0,  # Will be updated after exchange execution
                status=OrderStatus.PENDING.value,
                exchange_order_id=None,  # Will be updated after exchange execution
                executed_at=None,  # Will be updated after exchange execution
                stop_loss=trade_order.stop_loss  # Store the user's intended stop loss
            )
            
            self.session.add(pending_trade)
            self.session.commit()
            self.session.refresh(pending_trade)
            logger.info(f"Pending trade record created in database: {pending_trade.id}")
            
            # Log activity for pending trade
            from app.services.activity_service import activity_service
            from app.schemas.activity import ActivityCreate
            from app.models.user import User
            
            user = self.session.query(User).filter(User.id == user_id).first()
            if user:
                activity_data = ActivityCreate(
                    type="MANUAL_TRADE_PENDING",
                    description=f"Manual spot {trade_order.side} order for {trade_order.amount} {trade_order.symbol.split('/')[0]} at market price. Status: PENDING (trade id: {pending_trade.id})",
                    amount=trade_order.amount
                )
                activity_service.log_activity(self.session, user, activity_data)
                logger.info(f"Activity logged for pending manual trade: {pending_trade.id}")
            
        except Exception as db_error:
            logger.error(f"Failed to create pending trade record in database: {db_error}")
            raise Exception(f"Failed to log trade in system: {db_error}")

        # STEP 2: Execute trade on exchange
        try:
            logger.info(f"Executing trade on exchange for user {user_id}: {trade_order.model_dump_json()}")
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
                # Update database with failed status
                pending_trade.status = OrderStatus.REJECTED.value
                pending_trade.exchange_order_id = str(order_result.id) if order_result.id else None
                self.session.commit()
                
                error_message = f"Trade failed on exchange with status: {order_status}"
                logger.error(f"Trade failed for user {user_id}. Reason: {error_message}")
                
                # Log failed trade activity
                if user:
                    activity_data = ActivityCreate(
                        type="MANUAL_TRADE_FAILED",
                        description=f"Manual trade failed for {trade_order.symbol}. Status: {order_status} (trade id: {pending_trade.id})",
                        amount=trade_order.amount
                    )
                    activity_service.log_activity(self.session, user, activity_data)
                
                raise Exception(error_message)

            # STEP 3: Update database with successful execution
            try:
                # Update main trade record
                pending_trade.status = OrderStatus.FILLED.value if order_result.status == "closed" else OrderStatus.OPEN.value
                # Robust executed price logic
                executed_price = order_result.price
                if not executed_price or executed_price == 0:
                    # Try to fetch the order details from the exchange using raw CCXT response
                    try:
                        # Get the raw CCXT response directly to access the 'average' field
                        raw_order = await exchange.client.fetch_order(order_result.id, trade_order.symbol)
                        logger.info(f"Raw order response: {raw_order}")
                        
                        # Use 'average' as the primary fill price for market orders (this is the actual executed price)
                        executed_price = raw_order.get('average')
                        if executed_price:
                            logger.info(f"Using 'average' field from raw order: {executed_price}")
                        else:
                            # Fallback to other fields
                            executed_price = (
                                raw_order.get('price') or
                                raw_order.get('executed_price') or
                                0
                            )
                            logger.info(f"Using fallback price from raw order: {executed_price}")
                            
                    except Exception as fetch_error:
                        logger.warning(f"Could not fetch executed price for order {order_result.id}: {fetch_error}")
                        # Fallback: fetch recent trades and match by order ID
                        try:
                            trades = await exchange.client.fetch_my_trades(trade_order.symbol)
                            for trade in trades:
                                if str(trade.get('order')) == str(order_result.id):
                                    executed_price = float(trade.get('price', 0))
                                    logger.info(f"Matched executed price from trade history: {executed_price}")
                                    break
                        except Exception as trade_fetch_error:
                            logger.warning(f"Could not fetch recent trades for executed price: {trade_fetch_error}")
                
                if not executed_price or executed_price == 0:
                    logger.error("Executed price is zero! This will cause downstream issues.")
                else:
                    logger.info(f"Final executed price: {executed_price}")
                    
                pending_trade.executed_price = float(executed_price)
                pending_trade.exchange_order_id = str(order_result.id)
                pending_trade.executed_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Trade record updated in database: {pending_trade.id}")

                # Create position record for successful trade
                try:
                    # For spot trading, create a position record
                    if trade_order.trade_type == "spot":
                        # Check if position already exists for this order
                        existing_position = self.session.query(Position).filter(
                            Position.exchange_order_id == str(order_result.id),
                            Position.symbol == trade_order.symbol,
                            Position.user_id == user_id
                        ).first()
                        
                        if existing_position:
                            logger.warning(f"Position already exists for order {order_result.id} - skipping creation")
                        else:
                            # Validate required fields before creating position
                            if not trade_order.amount or trade_order.amount <= 0:
                                raise ValueError(f"Invalid trade amount: {trade_order.amount}")
                            
                            if not order_result.price and not trade_order.price:
                                raise ValueError("No price available for position creation")
                            
                            entry_price = float(order_result.price) if order_result.price else float(trade_order.price or 0)
                            
                            position = Position(
                                user_id=user_id,
                                exchange_connection_id=exchange_conn.id,
                                symbol=trade_order.symbol,
                                trade_type=trade_order.trade_type,  # Use actual trade type
                                side=trade_order.side,
                                quantity=trade_order.amount,
                                entry_price=entry_price,
                                current_price=entry_price,
                                leverage=1,  # Spot trading has leverage of 1
                                exchange_order_id=str(order_result.id),  # Store the exchange order ID
                                unrealized_pnl=0.0,  # Will be calculated later
                                realized_pnl=0.0,
                                total_pnl=0.0,
                                is_open=True,
                                opened_at=datetime.utcnow()
                            )
                            
                            self.session.add(position)
                            self.session.commit()
                            logger.info(f"Position record created for manual trade: {position.id} with order ID {order_result.id}")
                            
                            # Verify position was created successfully
                            created_position = self.session.query(Position).filter(
                                Position.id == position.id
                            ).first()
                            
                            if not created_position:
                                raise Exception("Position was not saved to database")
                            
                except Exception as pos_error:
                    logger.error(f"Failed to create position record: {pos_error}")
                    logger.error(f"Position creation error details: {type(pos_error).__name__}: {str(pos_error)}")
                    logger.error(f"Trade details - Order ID: {order_result.id}, Symbol: {trade_order.symbol}, Amount: {trade_order.amount}, Price: {order_result.price}")
                    # Don't fail the trade if position creation fails, but log the error for investigation

                # Log successful trade activity
                if user:
                    status_text = "closed" if order_result.status == "closed" else "open"
                    activity_data = ActivityCreate(
                        type="MANUAL_TRADE",
                        description=f"Manual spot {trade_order.side} order for {trade_order.amount} {trade_order.symbol.split('/')[0]} at market price. Status: {status_text} (trade id: {pending_trade.id})",
                        amount=trade_order.amount
                    )
                    activity_service.log_activity(self.session, user, activity_data)
                    logger.info(f"Activity logged for successful manual trade: {pending_trade.id}")

                # Set up EMA25 trailing stop loss management if enabled
                if trade_order.enable_ema25_trailing and trade_order.stop_loss:
                    try:
                        from app.tasks.manual_stop_loss_tasks import setup_manual_ema25_trailing
                        
                        # Schedule the EMA25 trailing setup task
                        setup_task = setup_manual_ema25_trailing.delay(pending_trade.id, user_id)
                        logger.info(f"EMA25 trailing setup scheduled for manual trade {pending_trade.id}, task ID: {setup_task.id}")
                        
                        # Log the EMA25 trailing setup
                        if user:
                            activity_data = ActivityCreate(
                                type="MANUAL_EMA25_SETUP_SCHEDULED",
                                description=f"EMA25 trailing stop loss management scheduled for manual trade {pending_trade.id} on {trade_order.symbol}",
                                amount=trade_order.stop_loss
                            )
                            activity_service.log_activity(self.session, user, activity_data)
                            
                    except Exception as ema25_error:
                        logger.error(f"Failed to schedule EMA25 trailing setup for trade {pending_trade.id}: {ema25_error}")
                        # Don't fail the trade if EMA25 setup fails

            except Exception as update_error:
                logger.error(f"Failed to update trade record in database: {update_error}")
                # Don't fail the entire operation if database update fails
                # The trade was successful on exchange, we just couldn't update our records

            # STEP 4: Create stop loss order if specified
            stop_loss_order = None
            logger.info(f"Checking for stop loss: trade_order.stop_loss = {trade_order.stop_loss}")
            if trade_order.stop_loss:
                logger.info(f"Stop loss value provided: {trade_order.stop_loss}")
                try:
                    # Use the new timeout handler for robust stop loss creation
                    from app.services.stop_loss_timeout_handler import create_stop_loss_safe
                    
                    stop_loss_order = await create_stop_loss_safe(
                        trade_order, user_id, exchange_conn, user, activity_service, exchange, self.session
                    )
                    
                    if stop_loss_order:
                        logger.info(f"Stop loss order created successfully using timeout handler")
                    else:
                        logger.warning("Stop loss creation failed, but main trade will continue")
                        
                except Exception as stop_loss_error:
                    error_msg = str(stop_loss_error)
                    logger.error(f"Failed to create stop loss order: {stop_loss_error}")
                    logger.error(f"Stop loss error details: {type(stop_loss_error).__name__}: {error_msg}")

                    # Categorize error types for better debugging
                    if "precision" in error_msg.lower():
                        logger.error("❌ PRECISION ERROR: Check price/amount decimal places")
                    elif "balance" in error_msg.lower() or "insufficient" in error_msg.lower():
                        logger.error("❌ BALANCE ERROR: Insufficient funds for stop loss")
                    elif "notional" in error_msg.lower() or "min" in error_msg.lower():
                        logger.error("❌ MINIMUM VALUE ERROR: Order below exchange minimums")
                    elif "order type" in error_msg.lower():
                        logger.error("❌ ORDER TYPE ERROR: Stop loss order type not supported")
                    elif "symbol" in error_msg.lower():
                        logger.error("❌ SYMBOL ERROR: Invalid trading pair")
                    elif "rate limit" in error_msg.lower():
                        logger.error("❌ RATE LIMIT ERROR: Too many requests to exchange")
                    else:
                        logger.error("❌ UNKNOWN ERROR: Check exchange connection and parameters")

                    # Log activity for stop loss failure
                    if user:
                        activity_data = ActivityCreate(
                            type="STOP_LOSS_ORDER_FAILED",
                            description=f"Failed to create stop loss order for {trade_order.symbol} at {trade_order.stop_loss}: {error_msg[:100]}...",
                            amount=trade_order.amount
                        )
                        activity_service.log_activity(self.session, user, activity_data)

                    # Don't fail the main trade if stop loss fails
                    logger.warning("Main trade will continue despite stop loss failure")
            else:
                logger.info("No stop loss value provided, skipping stop loss order creation")

            # Return the result
            trade_result = TradeResult(
                id=str(order_result.id),
                symbol=order_result.symbol,
                price=float(order_result.price or 0),
                amount=float(order_result.amount),
                status=order_status or "unknown",
            )
            logger.info(f"Trade executed successfully: {trade_result.model_dump_json()}")
            return trade_result

        except Exception as exchange_error:
            # Update database with failed status if exchange execution fails
            try:
                pending_trade.status = OrderStatus.REJECTED.value
                self.session.commit()
                
                # Log failed trade activity
                if user:
                    activity_data = ActivityCreate(
                        type="MANUAL_TRADE_FAILED",
                        description=f"Manual trade failed for {trade_order.symbol}. Exchange error: {exchange_error} (trade id: {pending_trade.id})",
                        amount=trade_order.amount
                    )
                    activity_service.log_activity(self.session, user, activity_data)
            except Exception as update_error:
                logger.error(f"Failed to update failed trade record: {update_error}")
            
            logger.error(f"Trade execution failed for user {user_id}: {exchange_error}", exc_info=True)
            raise exchange_error
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