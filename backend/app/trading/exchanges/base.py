from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeType(str, Enum):
    SPOT = "spot"
    FUTURES = "futures"


@dataclass
class Ticker:
    """Market ticker information"""
    symbol: str
    last_price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    timestamp: Optional[datetime] = None


@dataclass
class OrderBook:
    """Order book data"""
    symbol: str
    bids: List[Dict[str, Union[Decimal, int]]]  # [price, amount]
    asks: List[Dict[str, Union[Decimal, int]]]  # [price, amount]
    timestamp: Optional[datetime] = None


@dataclass
class Trade:
    """Trade information"""
    id: str
    symbol: str
    side: OrderSide
    amount: Decimal
    price: Decimal
    fee: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class Order:
    """Order information"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: Decimal
    price: Optional[Decimal] = None
    filled_amount: Decimal = Decimal('0')
    remaining_amount: Decimal = Decimal('0')
    status: str = "pending"
    fee: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class Balance:
    """Account balance information"""
    currency: str
    free: Decimal
    used: Decimal
    total: Decimal


@dataclass
class Position:
    """Position information for futures trading"""
    symbol: str
    side: OrderSide
    size: Decimal
    entry_price: Decimal
    mark_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    leverage: Optional[int] = None
    liquidation_price: Optional[Decimal] = None


class BaseExchange(ABC):
    """Base class for all exchange connectors"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None, is_testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.is_testnet = is_testnet
        self.exchange_name = self.__class__.__name__.lower().replace('exchange', '')
        
        logger.info(f"Base for {self.exchange_name} initialized", testnet=is_testnet)
    
    @abstractmethod
    async def close(self):
        """Close the exchange connection and any underlying clients."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker for a symbol"""
        pass
    
    @abstractmethod
    async def get_tickers(self, symbols: List[str]) -> Dict[str, Ticker]:
        """Get tickers for a list of symbols"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get order book for a symbol"""
        pass
    
    @abstractmethod
    async def get_balance(self, currency: Optional[str] = None) -> List[Balance]:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def create_order(self, symbol: str, order_type: OrderType, side: OrderSide,
                          amount: Decimal, price: Optional[Decimal] = None,
                          params: Optional[Dict[str, Any]] = None) -> Order:
        """Create a new order"""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get order information"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders"""
        pass
    
    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions (for futures)"""
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for futures trading"""
        pass
    
    @abstractmethod
    async def get_symbols(self) -> List[str]:
        """Get available trading symbols"""
        pass
    
    @abstractmethod
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and trading rules"""
        pass
    
    @abstractmethod
    async def get_historical_klines(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Get historical klines for a symbol"""
        pass
    
    async def test_connection(self) -> bool:
        """Test if the exchange connection is working using a public endpoint."""
        try:
            # Using a public endpoint is better for a general connection test
            info = await self.get_exchange_info()
            if info:
                logger.info(f"Connection test successful for {self.exchange_name}")
                return True
            else:
                logger.warning(f"Connection test for {self.exchange_name} returned no info.")
                return False
        except Exception as e:
            logger.error(f"Connection test failed for {self.exchange_name}: {e}", exc_info=True)
            return False
    
    def get_exchange_name(self) -> str:
        """Get the exchange name"""
        return self.exchange_name
    
    def is_testnet_mode(self) -> bool:
        """Check if running in testnet mode"""
        return self.is_testnet
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close() 