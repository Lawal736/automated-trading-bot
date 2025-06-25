import ccxt.async_support as ccxt
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

from app.trading.exchanges.base import (
    BaseExchange, Ticker, OrderBook, Trade, Order, Balance, Position,
    OrderType, OrderSide, TradeType
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class GateioExchange(BaseExchange):
    """Gate.io exchange connector"""
    
    def __init__(self, api_key: str, api_secret: str, passphrase: Optional[str] = None, is_testnet: bool = False):
        super().__init__(api_key, api_secret, is_testnet)
        self.exchange_name = "gateio"
        exchange_class = getattr(ccxt, self.exchange_name)

        config = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'password': passphrase,
            'options': {
                'defaultType': 'spot',
            },
        }

        if self.is_testnet:
            config['options']['testnet'] = True

        self.client = exchange_class(config)
        
        futures_config = {
            **config,
            'options': {
                'defaultType': 'swap',
            }
        }
        self.futures_client = exchange_class(futures_config)
        logger.info(f"GateioExchange initialized for {'testnet' if is_testnet else 'mainnet'}")

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get current ticker for a symbol"""
        try:
            ticker = await self.client.fetch_ticker(symbol)
            return Ticker(
                symbol=symbol,
                last_price=Decimal(str(ticker['last'])),
                bid=Decimal(str(ticker['bid'])) if ticker['bid'] else None,
                ask=Decimal(str(ticker['ask'])) if ticker['ask'] else None,
                high=Decimal(str(ticker['high'])) if ticker['high'] else None,
                low=Decimal(str(ticker['low'])) if ticker['low'] else None,
                volume=Decimal(str(ticker['baseVolume'])) if ticker['baseVolume'] else None,
                timestamp=datetime.fromtimestamp(ticker['timestamp'] / 1000) if ticker['timestamp'] else None
            )
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
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
    
    async def create_order(self, symbol: str, order_type: OrderType, side: OrderSide,
                          amount: Decimal, price: Optional[Decimal] = None,
                          trade_type: TradeType = TradeType.SPOT, **kwargs) -> Order:
        """Create a new order"""
        try:
            # Choose appropriate client based on trade type
            client = self.futures_client if trade_type == TradeType.FUTURES else self.client
            
            # Convert order type to Gate.io format
            gateio_order_type = order_type.value.lower()
            if order_type == OrderType.STOP:
                gateio_order_type = 'stop_market' if price is None else 'stop_limit'
            elif order_type == OrderType.STOP_LIMIT:
                gateio_order_type = 'stop_limit'
            
            order_params = {
                'symbol': symbol,
                'type': gateio_order_type,
                'side': side.value.lower(),
                'amount': float(amount),
            }
            
            if price is not None:
                order_params['price'] = float(price)
            
            # Add additional parameters
            order_params.update(kwargs)
            
            result = await client.create_order(**order_params)
            
            return Order(
                id=str(result['id']),
                symbol=symbol,
                side=side,
                order_type=order_type,
                amount=amount,
                price=price,
                status=result['status'],
                timestamp=datetime.fromtimestamp(result['timestamp'] / 1000) if result['timestamp'] else None
            )
        except Exception as e:
            logger.error(f"Error creating order for {symbol}: {e}")
            raise
    
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get order information"""
        try:
            result = await self.client.fetch_order(order_id, symbol)
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
            logger.error(f"Error fetching order {order_id}: {e}")
            raise
    
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
        """Get current positions (for futures)"""
        try:
            positions = await self.futures_client.fetch_positions(symbol)
            result = []
            
            for pos in positions:
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
        try:
            markets = await self.client.load_markets()
            return list(markets.keys())
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            raise
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and trading rules"""
        try:
            info = await self.client.fetch_exchange_info()
            return {
                'timezone': info.get('timezone'),
                'serverTime': info.get('serverTime'),
                'rateLimits': info.get('rateLimits'),
                'symbols': len(info.get('symbols', [])),
                'status': info.get('status')
            }
        except Exception as e:
            logger.error(f"Error fetching exchange info: {e}")
            raise
    
    async def close(self):
        """Close the exchange connection"""
        try:
            await self.client.close()
            await self.futures_client.close()
            logger.info("Gate.io exchange connections closed")
        except Exception as e:
            logger.error(f"Error closing Gate.io connections: {e}") 