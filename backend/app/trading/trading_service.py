from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.trading.exchanges.factory import ExchangeFactory
from app.trading.exchanges.base import (
    BaseExchange, Ticker, OrderBook, Trade, Order, Balance, Position,
    OrderType, OrderSide, TradeType
)
from app.models.exchange import ExchangeConnection
from app.models.user import User
from app.models.bot import Bot
from app.models.strategy import Strategy
from app.models.trading import Trade, Position
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class TradingService:
    """Unified trading service for managing multiple exchange connections"""
    
    def __init__(self, exchange_factory: ExchangeFactory):
        self._exchanges: Dict[str, BaseExchange] = {}
        self._connection_map: Dict[int, str] = {}  # connection_id -> exchange_name
        self._factory = exchange_factory
    
    async def validate_credentials(self, exchange_name: str, api_key: str, api_secret: str, is_testnet: bool, password: Optional[str] = None) -> bool:
        """Validate API credentials by attempting to connect and fetch balance."""
        try:
            temp_exchange = self._factory.create_exchange(
                exchange_name=exchange_name,
                api_key=api_key,
                api_secret=api_secret,
                is_testnet=is_testnet,
                password=password
            )
            await temp_exchange.get_balance()  # Test a private endpoint
            await temp_exchange.close()
            return True
        except Exception as e:
            logger.error(f"Credential validation failed for {exchange_name}: {e}")
            return False
    
    async def add_exchange_connection(self, connection: ExchangeConnection) -> bool:
        """Add an exchange connection to the trading service"""
        try:
            # Only pass 'password' as 'passphrase' for Kucoin
            if connection.exchange_name.lower() == 'kucoin':
                exchange = self._factory.create_exchange(
                    exchange_name=connection.exchange_name,
                    api_key=connection.api_key,
                    api_secret=connection.api_secret,
                    password=connection.password,  # Kucoin uses 'password' as 'passphrase'
                    is_testnet=connection.is_testnet
                )
            else:
                exchange = self._factory.create_exchange(
                    exchange_name=connection.exchange_name,
                    api_key=connection.api_key,
                    api_secret=connection.api_secret,
                    is_testnet=connection.is_testnet
                )

            # Test a private endpoint to validate credentials
            await exchange.get_balance()

            self._exchanges[connection.exchange_name.lower()] = exchange
            self._connection_map[connection.id] = connection.exchange_name.lower()

            logger.info(f"Added and verified exchange connection: {connection.exchange_name} (ID: {connection.id})")
            return True

        except Exception as e:
            logger.error(f"Failed to add exchange connection {connection.exchange_name}: {e}", exc_info=True)
            # Ensure partially added connections are cleaned up
            await self.remove_exchange_connection(connection.id)
            return False
    
    async def remove_exchange_connection(self, connection_id: int) -> bool:
        """Remove an exchange connection from the trading service"""
        try:
            if connection_id in self._connection_map:
                exchange_name = self._connection_map[connection_id]
                
                if exchange_name in self._exchanges:
                    exchange = self._exchanges[exchange_name]
                    await exchange.close()
                    del self._exchanges[exchange_name]
                
                del self._connection_map[connection_id]
                
                logger.info(f"Removed exchange connection: {exchange_name} (ID: {connection_id})")
                return True
            else:
                logger.warning(f"Connection ID {connection_id} not found in trading service")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove exchange connection {connection_id}: {e}")
            return False
    
    async def get_exchange(self, exchange_name: str) -> Optional[BaseExchange]:
        """Get an exchange connector by name"""
        return self._exchanges.get(exchange_name.lower())
    
    async def get_exchange_by_connection_id(self, connection_id: int) -> Optional[BaseExchange]:
        """Get an exchange connector by connection ID"""
        exchange_name = self._connection_map.get(connection_id)
        if exchange_name:
            return await self.get_exchange(exchange_name)
        return None
    
    async def get_all_exchanges(self) -> List[BaseExchange]:
        """Get all active exchange connectors"""
        return list(self._exchanges.values())
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all exchange connections"""
        status = {}
        
        for connection_id, exchange_name in self._connection_map.items():
            exchange = self._exchanges.get(exchange_name)
            if exchange:
                try:
                    # test_connection uses a public endpoint, good for a health check
                    is_connected = await exchange.test_connection()
                    status[exchange_name] = {
                        'connection_id': connection_id,
                        'connected': is_connected,
                        'testnet': exchange.is_testnet,
                        'exchange_name': exchange.exchange_name
                    }
                except Exception as e:
                    status[exchange_name] = {
                        'connection_id': connection_id,
                        'connected': False,
                        'error': str(e)
                    }
        
        return status
    
    # Unified trading methods that work across all exchanges
    
    async def get_ticker(self, symbol: str, exchange_name: Optional[str] = None) -> Optional[Ticker]:
        """Get ticker for a symbol from specified exchange or all exchanges"""
        if exchange_name:
            exchange = await self.get_exchange(exchange_name)
            if exchange:
                return await exchange.get_ticker(symbol)
            return None
        
        # Get from all exchanges and return the first successful result
        for exchange in self._exchanges.values():
            try:
                return await exchange.get_ticker(symbol)
            except Exception as e:
                logger.warning(f"Failed to get ticker from {exchange.get_exchange_name()}: {e}")
                continue
        
        return None
    
    async def get_order_book(self, symbol: str, exchange_name: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book for a symbol from specified exchange"""
        exchange = await self.get_exchange(exchange_name)
        if exchange:
            return await exchange.get_order_book(symbol, limit)
        return None
    
    async def get_balance(self, exchange_name: str, currency: Optional[str] = None) -> List[Balance]:
        """Get balance from specified exchange"""
        exchange = await self.get_exchange(exchange_name)
        if exchange:
            return await exchange.get_balance(currency)
        return []
    
    async def create_order(self, connection_id: int, symbol: str, order_type: OrderType,
                          side: OrderSide, amount: Decimal, price: Optional[Decimal] = None,
                          params: Optional[Dict[str, Any]] = None) -> Optional[Order]:
        """Create an order using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.create_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
        return None
    
    async def get_order(self, connection_id: int, order_id: str, symbol: str) -> Optional[Order]:
        """Get order information using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.get_order(order_id, symbol)
        return None
    
    async def cancel_order(self, connection_id: int, order_id: str, symbol: str) -> bool:
        """Cancel an order using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.cancel_order(order_id, symbol)
        return False
    
    async def get_open_orders(self, connection_id: int, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.get_open_orders(symbol)
        return []
    
    async def get_trades(self, connection_id: int, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.get_trades(symbol, limit)
        return []
    
    async def get_positions(self, connection_id: int, symbol: Optional[str] = None) -> List[Position]:
        """Get positions using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.get_positions(symbol)
        return []
    
    async def set_leverage(self, connection_id: int, symbol: str, leverage: int) -> bool:
        """Set leverage using the specified connection"""
        exchange = await self.get_exchange_by_connection_id(connection_id)
        if exchange:
            return await exchange.set_leverage(symbol, leverage)
        return False
    
    async def get_symbols(self, exchange_name: str) -> List[str]:
        """Get available symbols from specified exchange"""
        exchange = await self.get_exchange(exchange_name)
        if exchange:
            return await exchange.get_symbols()
        return []
    
    async def get_exchange_info(self, exchange_name: str) -> Dict[str, Any]:
        """Get exchange information from specified exchange"""
        exchange = await self.get_exchange(exchange_name)
        if exchange:
            return await exchange.get_exchange_info()
        return {}
    
    async def close_all_connections(self):
        """Close all exchange connections"""
        for exchange in self._exchanges.values():
            try:
                await exchange.close()
            except Exception as e:
                logger.error(f"Error closing exchange connection: {e}")
        
        self._exchanges.clear()
        self._connection_map.clear()
        logger.info("All exchange connections closed")


# Global trading service instance - This might be removed if using dependency injection everywhere
factory = ExchangeFactory()
trading_service = TradingService(exchange_factory=factory) 