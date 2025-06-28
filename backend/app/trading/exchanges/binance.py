import ccxt.async_support as ccxt
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import decimal
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from app.trading.exchanges.base import (
    BaseExchange, OrderBook, Trade, Order, Balance, Position,
    OrderType, OrderSide, TradeType
)
from app.schemas.ticker import Ticker
from app.core.logging import get_logger

logger = get_logger(__name__)


class BinanceExchange(BaseExchange):
    """Binance exchange connector"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None, is_testnet: bool = True):
        super().__init__(api_key, api_secret, passphrase, is_testnet)
        
        common_config = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {'adjustForTimeDifference': True},
        }

        # Initialize Spot Client
        spot_config = common_config.copy()
        if self.is_testnet:
            spot_config['options']['defaultType'] = 'spot'
            self.client = ccxt.binance(spot_config)
            self.client.set_sandbox_mode(True)
        else:
            self.client = ccxt.binance(spot_config)

        # Initialize Futures Client
        futures_config = common_config.copy()
        if self.is_testnet:
            futures_config['options']['defaultType'] = 'future'
            self.futures_client = ccxt.binance(futures_config)
            self.futures_client.set_sandbox_mode(True)
        else:
            futures_config['options']['defaultType'] = 'future'
            self.futures_client = ccxt.binance(futures_config)

        logger.info(f"BinanceExchange initialized for {'testnet' if is_testnet else 'mainnet'}")

    def _get_client_for_symbol(self, symbol: str):
        # A simple heuristic to decide client.
        # Production systems might need a more robust way to check if a symbol is spot or futures.
        return self.futures_client if 'PERP' in symbol.upper() else self.client

    async def close(self):
        """Close exchange connections"""
        if self.client:
            await self.client.close()
        if self.futures_client:
            await self.futures_client.close()
        logger.info("BinanceExchange connections closed.")

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current market ticker for a symbol"""
        if not self.client:
            await self.initialize()

        try:
            ticker_data = await self.client.fetch_ticker(symbol)
            if not ticker_data or 'last' not in ticker_data:
                logger.warning(f"Invalid or empty ticker response for {symbol} from Binance.")
                return None
            return self._parse_ticker(ticker_data)
        
        except ccxt.BadSymbol as e:
            # This is not an error, it just means the symbol doesn't exist on the exchange.
            # Log as a warning without the full stack trace for cleaner logs.
            logger.warning(f"Symbol not found on Binance for get_ticker: {symbol}. Error: {e}")
            return None
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching ticker for {symbol} on Binance: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_ticker for {symbol}: {e}", exc_info=True)
            return None

    async def get_historical_klines(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Get historical klines for a symbol"""
        client = self._get_client_for_symbol(symbol)
        try:
            ohlcv = await client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching historical klines for {symbol}: {e}")
            raise

    def _parse_ticker(self, ticker_data: dict) -> Optional[Ticker]:
        """Parse raw ticker data into a Ticker object"""
        try:
            logger.info(f"Parsing ticker data: {ticker_data}")
            last = ticker_data.get('last')
            logger.info(f"Last price value: {last} (type: {type(last)})")
            if last is None:
                logger.warning(f"Ticker data for {ticker_data.get('symbol', 'unknown')} has no last price.")
                return None
            try:
                last_price = Decimal(str(last))
                logger.info(f"Converted last_price: {last_price}")
            except (ValueError, TypeError, decimal.InvalidOperation):
                logger.warning(f"Invalid last price value for {ticker_data.get('symbol', 'unknown')}: {last}")
                return None
            timestamp = ticker_data.get('timestamp')
            if timestamp is not None:
                dt = datetime.fromtimestamp(timestamp / 1000)
            else:
                dt = datetime.utcnow()
            ticker = Ticker(
                symbol=ticker_data['symbol'],
                last_price=last_price,
                timestamp=dt
            )
            logger.info(f"Created ticker object: {ticker}")
            return ticker
        except Exception as e:
            logger.error(f"Error parsing ticker data for {ticker_data.get('symbol', 'unknown')}: {e}")
            return None

    async def get_tickers(self, symbols: List[str]) -> Dict[str, Ticker]:
        """Fetch current market tickers for multiple symbols."""
        if not self.client:
            await self.initialize()

        result = {}
        
        try:
            # Try batch fetch first
            tickers_data = await self.client.fetch_tickers(symbols)
            for symbol, data in tickers_data.items():
                try:
                    result[symbol] = self._parse_ticker(data)
                except Exception as e:
                    logger.warning(f"Failed to parse ticker data for {symbol}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Batch ticker fetch failed: {e}. Falling back to individual fetching.")
            # Fallback to individual fetching
            for symbol in symbols:
                try:
                    ticker = await self.get_ticker(symbol)
                    if ticker:
                        result[symbol] = ticker
                except Exception as e_ind:
                    logger.warning(f"Failed to fetch individual ticker for {symbol}: {e_ind}")
                    continue
        
        return result
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get order book for a symbol"""
        try:
            order_book = await self.client.fetch_order_book(symbol, limit)
            return OrderBook(
                symbol=symbol,
                bids=[{'price': Decimal(str(bid[0])), 'amount': Decimal(str(bid[1]))} for bid in order_book['bids']],
                asks=[{'price': Decimal(str(ask[0])), 'amount': Decimal(str(ask[1]))} for ask in order_book['asks']],
                timestamp=datetime.fromtimestamp(order_book['timestamp'] / 1000) if order_book['timestamp'] else None
            )
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise
    
    async def get_balance(self, currency: Optional[str] = None) -> List[Balance]:
        """Get account balance"""
        try:
            balance = await self.client.fetch_balance()
            balances = []
            
            for curr, bal in balance['total'].items():
                if bal > 0 or (currency and curr == currency):
                    balances.append(Balance(
                        currency=curr,
                        free=Decimal(str(balance['free'].get(curr, 0))),
                        used=Decimal(str(balance['used'].get(curr, 0))),
                        total=Decimal(str(bal))
                    ))
            
            if currency:
                return [b for b in balances if b.currency == currency]
            return balances
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
    async def get_futures_balance(self, currency: Optional[str] = None) -> List[Balance]:
        """Get futures account balance"""
        try:
            balance = await self.futures_client.fetch_balance()
            balances = []
            
            for curr, bal in balance['total'].items():
                if bal > 0 or (currency and curr == currency):
                    balances.append(Balance(
                        currency=curr,
                        free=Decimal(str(balance['free'].get(curr, 0))),
                        used=Decimal(str(balance['used'].get(curr, 0))),
                        total=Decimal(str(bal))
                    ))
            
            if currency:
                return [b for b in balances if b.currency == currency]
            return balances
        except Exception as e:
            logger.error(f"Error fetching futures balance: {e}")
            raise
    
    async def create_order(self, symbol: str, order_type: OrderType, side: OrderSide,
                          amount: Decimal, price: Optional[Decimal] = None,
                          params: Optional[Dict[str, Any]] = None) -> Order:
        """Create a new order"""
        client = self._get_client_for_symbol(symbol)
        try:
            order_params = params or {}
            
            # Map order type for Binance compatibility
            binance_order_type = order_type if isinstance(order_type, str) else order_type.value
            if binance_order_type == "stop_limit":
                binance_order_type = "STOP_LOSS_LIMIT"
            
            result = await client.create_order(
                symbol=symbol,
                type=binance_order_type,
                side=side if isinstance(side, str) else side.value,
                amount=float(amount),
                price=float(price) if price else None,
                params=order_params
            )
            return self._parse_order(result)
        except Exception as e:
            logger.error(f"Error creating order for {symbol} on Binance: {e}", exc_info=True)
            raise
    
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get order information, with fallback to trade history if not found"""
        try:
            logger.info(f"[Binance] Fetching order {order_id} for {symbol}")
            result = await self.client.fetch_order(order_id, symbol)
            logger.info(f"[Binance] fetch_order result: {result}")
            return Order(
                id=str(result['id']),
                symbol=symbol,
                side=OrderSide.BUY if result['side'] == 'buy' else OrderSide.SELL,
                order_type=OrderType(result['type'].lower()),
                amount=Decimal(str(result['amount'])),
                price=Decimal(str(result['price'])) if result['price'] else None,
                filled_amount=Decimal(str(result['filled'])),
                remaining_amount=Decimal(str(result['remaining'])),
                status=result['status'],
                fee=Decimal(str(result['fee']['cost'])) if result['fee'] else None,
                fee_currency=result['fee']['currency'] if result['fee'] else None,
                timestamp=datetime.fromtimestamp(result['timestamp'] / 1000) if result['timestamp'] else None
            )
        except Exception as e:
            logger.warning(f"[Binance] fetch_order failed for {order_id} on {symbol}: {e}")
            # Fallback: check trade history for this symbol
            try:
                logger.info(f"[Binance] Falling back to trade history for {symbol}")
                trades = await self.client.fetch_my_trades(symbol)
                logger.info(f"[Binance] Trade history fetched: {len(trades)} trades")
                for trade in trades:
                    if str(trade['order']) == str(order_id):
                        logger.info(f"[Binance] Found order {order_id} in trade history for {symbol}")
                        # Synthesize an Order object as filled
                        return Order(
                            id=str(trade['order']),
                            symbol=symbol,
                            side=OrderSide.BUY if trade['side'] == 'buy' else OrderSide.SELL,
                            order_type=OrderType('market'),
                            amount=Decimal(str(trade['amount'])),
                            price=Decimal(str(trade['price'])),
                            filled_amount=Decimal(str(trade['amount'])),
                            remaining_amount=Decimal('0'),
                            status='filled',
                            fee=Decimal(str(trade['fee']['cost'])) if trade['fee'] else None,
                            fee_currency=trade['fee']['currency'] if trade['fee'] else None,
                            timestamp=datetime.fromtimestamp(trade['timestamp'] / 1000) if trade['timestamp'] else None
                        )
                logger.warning(f"[Binance] Order {order_id} not found in trade history for {symbol}")
                return None
            except Exception as e2:
                logger.error(f"[Binance] fetch_my_trades failed for {symbol}: {e2}")
                return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            result = await self.client.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} cancelled successfully")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders"""
        try:
            orders = await self.client.fetch_open_orders(symbol)
            result = []
            
            for order in orders:
                result.append(Order(
                    id=str(order['id']),
                    symbol=order['symbol'],
                    side=OrderSide.BUY if order['side'] == 'buy' else OrderSide.SELL,
                    order_type=OrderType(order['type'].lower()),
                    amount=Decimal(str(order['amount'])),
                    price=Decimal(str(order['price'])) if order['price'] else None,
                    filled_amount=Decimal(str(order['filled'])),
                    remaining_amount=Decimal(str(order['remaining'])),
                    status=order['status'],
                    timestamp=datetime.fromtimestamp(order['timestamp'] / 1000) if order['timestamp'] else None
                ))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            raise
    
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        try:
            trades = await self.client.fetch_trades(symbol, limit=limit)
            result = []
            
            for trade in trades:
                result.append(Trade(
                    id=str(trade['id']),
                    symbol=symbol,
                    side=OrderSide.BUY if trade['side'] == 'buy' else OrderSide.SELL,
                    amount=Decimal(str(trade['amount'])),
                    price=Decimal(str(trade['price'])),
                    fee=Decimal(str(trade['fee']['cost'])) if trade['fee'] else None,
                    fee_currency=trade['fee']['currency'] if trade['fee'] else None,
                    timestamp=datetime.fromtimestamp(trade['timestamp'] / 1000) if trade['timestamp'] else None
                ))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {e}")
            raise
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions (for both spot and futures)"""
        try:
            result = []
            
            # For spot trading, get balances and convert to positions
            try:
                balances = await self.get_balance()
                for balance in balances:
                    if balance.total > 0 and balance.currency != 'USDT':  # Skip USDT and zero balances
                        # Create a position-like object for spot holdings
                        symbol_name = f"{balance.currency}/USDT"
                        if symbol and symbol != symbol_name:
                            continue
                            
                        # Get current price for PnL calculation
                        try:
                            ticker = await self.get_ticker(symbol_name)
                            current_price = float(ticker.price) if ticker else 0
                        except:
                            current_price = 0
                        
                        result.append(Position(
                            symbol=symbol_name,
                            side=OrderSide.BUY,  # Spot holdings are always "buy" side
                            size=balance.total,
                            entry_price=Decimal('0'),  # We don't have entry price for spot balances
                            mark_price=Decimal(str(current_price)),
                            unrealized_pnl=Decimal('0'),  # Can't calculate without entry price
                            realized_pnl=Decimal('0'),
                            leverage=None,
                            liquidation_price=None
                        ))
            except Exception as e:
                logger.warning(f"Error fetching spot positions: {e}")
            
            # For futures trading, get positions
            try:
                futures_positions = await self.futures_client.fetch_positions(symbol)
                for pos in futures_positions:
                    if pos['size'] > 0:  # Only include open positions
                        result.append(Position(
                            symbol=pos['symbol'],
                            side=OrderSide.BUY if pos['side'] == 'long' else OrderSide.SELL,
                            size=Decimal(str(pos['size'])),
                            entry_price=Decimal(str(pos['entryPrice'])),
                            mark_price=Decimal(str(pos['markPrice'])) if pos['markPrice'] else None,
                            unrealized_pnl=Decimal(str(pos['unrealizedPnl'])) if pos['unrealizedPnl'] else None,
                            realized_pnl=Decimal(str(pos['realizedPnl'])) if pos['realizedPnl'] else None,
                            leverage=int(pos['leverage']) if pos['leverage'] else None,
                            liquidation_price=Decimal(str(pos['liquidationPrice'])) if pos['liquidationPrice'] else None
                        ))
            except Exception as e:
                logger.warning(f"Error fetching futures positions: {e}")
            
            return result
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for futures trading"""
        try:
            await self.futures_client.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error setting leverage for {symbol}: {e}")
            return False
    
    async def get_symbols(self) -> List[str]:
        """Get available trading symbols"""
        await self._load_markets_if_needed()
        spot_symbols = self.client.symbols
        futures_symbols = self.futures_client.symbols
        return sorted(list(set((spot_symbols or []) + (futures_symbols or []))))
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and trading rules"""
        await self._load_markets_if_needed()
        # Combining info from both clients, a real implementation might need to merge this smartly
        return {
            'spot': self.client.describe(),
            'futures': self.futures_client.describe(),
        }

    async def _load_markets_if_needed(self):
        if not self.client.markets:
            await self.client.load_markets()
        if not self.futures_client.markets:
            await self.futures_client.load_markets()

    def _parse_order(self, order_data: dict) -> Order:
        # Handle fee conversion safely
        fee = None
        fee_currency = None
        if order_data.get('fee'):
            try:
                fee_cost = order_data['fee'].get('cost')
                if fee_cost is not None and fee_cost != 0:
                    fee = Decimal(str(fee_cost))
                fee_currency = order_data['fee'].get('currency')
            except (ValueError, TypeError, decimal.InvalidOperation):
                # If fee conversion fails, set to None
                fee = None
                fee_currency = order_data['fee'].get('currency')
        
        return Order(
            id=str(order_data['id']),
            symbol=order_data['symbol'],
            side=OrderSide(order_data['side']),
            order_type=OrderType(order_data['type']),
            amount=Decimal(str(order_data['amount'])),
            price=Decimal(str(order_data['price'])) if order_data.get('price') else None,
            filled_amount=Decimal(str(order_data['filled'])),
            remaining_amount=Decimal(str(order_data['remaining'])),
            status=order_data['status'],
            fee=fee,
            fee_currency=fee_currency,
            timestamp=datetime.fromtimestamp(order_data['timestamp'] / 1000) if order_data.get('timestamp') else None
        ) 