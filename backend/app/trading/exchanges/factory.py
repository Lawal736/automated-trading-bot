from typing import Dict, Optional, Type
from app.trading.exchanges.base import BaseExchange
from app.trading.exchanges.binance import BinanceExchange
from app.trading.exchanges.gateio import GateioExchange
from app.trading.exchanges.kucoin import KucoinExchange
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExchangeFactory:
    """Factory for creating exchange connectors"""
    
    # Registry of available exchanges
    _exchanges: Dict[str, Type[BaseExchange]] = {
        'binance': BinanceExchange,
        'gateio': GateioExchange,
        'kucoin': KucoinExchange,
        # Add more exchanges as they are implemented
        # 'bingx': BingXExchange,
        # 'bitget': BitgetExchange,
    }
    
    @classmethod
    def get_available_exchanges(cls) -> list:
        """Get list of available exchange names"""
        return list(cls._exchanges.keys())
    
    @classmethod
    def create_exchange(cls, exchange_name: str, api_key: Optional[str] = None,
                       api_secret: Optional[str] = None, password: Optional[str] = None,
                       is_testnet: bool = True) -> BaseExchange:
        """Create an exchange connector instance"""
        
        exchange_name = exchange_name.lower()
        
        if exchange_name not in cls._exchanges:
            available = ', '.join(cls.get_available_exchanges())
            raise ValueError(f"Exchange '{exchange_name}' not supported. Available: {available}")
        
        exchange_class = cls._exchanges[exchange_name]
        
        try:
            # For KuCoin, the 'password' is the 'passphrase'
            if exchange_name == 'kucoin':
                exchange = exchange_class(
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=password, # Use password as passphrase
                    is_testnet=is_testnet
                )
            else:
                exchange = exchange_class(
                    api_key=api_key,
                    api_secret=api_secret,
                    is_testnet=is_testnet
                )
            
            logger.info(f"Created {exchange_name} exchange connector")
            return exchange
            
        except Exception as e:
            logger.error(f"Failed to create {exchange_name} exchange connector: {e}")
            raise
    
    @classmethod
    def register_exchange(cls, name: str, exchange_class: Type[BaseExchange]):
        """Register a new exchange connector"""
        cls._exchanges[name.lower()] = exchange_class
        logger.info(f"Registered exchange connector: {name}")
    
    @classmethod
    def is_supported(cls, exchange_name: str) -> bool:
        """Check if an exchange is supported"""
        return exchange_name.lower() in cls._exchanges
    
    @classmethod
    def get_exchange_info(cls, exchange_name: str) -> Dict:
        """Get information about an exchange"""
        exchange_name = exchange_name.lower()
        
        if not cls.is_supported(exchange_name):
            return {}
        
        exchange_class = cls._exchanges[exchange_name]
        
        return {
            'name': exchange_name,
            'class': exchange_class.__name__,
            'module': exchange_class.__module__,
            'doc': exchange_class.__doc__ or "No description available"
        } 