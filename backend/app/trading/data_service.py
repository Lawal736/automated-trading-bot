import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
import logging
from app.core.logging import get_logger

logger = get_logger(__name__)

class BinanceDataService:
    """Service to fetch market data from Binance API"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_klines(self, symbol: str, interval: str, limit: int = 500, start_time: Optional[int] = None, end_time: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch kline/candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Time interval ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M')
            limit: Number of klines to fetch (max 1000)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore]
        """
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'limit': min(limit, 1000)
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            url = f"{self.base_url}/ticker/price"
            params = {'symbol': symbol.upper()}
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return float(data['price'])
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def get_24hr_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24-hour ticker statistics"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            params = {'symbol': symbol.upper()}
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching 24hr ticker for {symbol}: {e}")
            return None
    
    def get_market_data_for_strategy(self, symbol: str, timeframe: str, lookback_periods: int = 100) -> pd.DataFrame:
        """
        Get market data optimized for strategy execution
        
        Args:
            symbol: Trading pair
            timeframe: Time interval
            lookback_periods: Number of periods to look back
            
        Returns:
            DataFrame with OHLCV data and technical indicators
        """
        try:
            # Fetch more data than needed to calculate indicators
            extra_periods = max(50, lookback_periods // 2)
            total_periods = lookback_periods + extra_periods
            
            df = self.get_klines(symbol, timeframe, limit=total_periods)
            
            if df.empty:
                return df
            
            # Add technical indicators
            df = self._add_technical_indicators(df)
            
            # Return only the requested number of periods
            return df.tail(lookback_periods)
            
        except Exception as e:
            logger.error(f"Error getting market data for strategy: {e}")
            return pd.DataFrame()
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the DataFrame"""
        try:
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Simple Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Exponential Moving Averages
            df['ema_7'] = df['close'].ewm(span=7).mean()
            df['ema_14'] = df['close'].ewm(span=14).mean()
            df['ema_21'] = df['close'].ewm(span=21).mean()
            
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'])
            
            # MACD
            macd_data = self._calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(df['close'])
            df['bb_upper'] = bb_data['upper']
            df['bb_middle'] = bb_data['middle']
            df['bb_lower'] = bb_data['lower']
            
            # ATR (Average True Range)
            df['atr'] = self._calculate_atr(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=prices.index)
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            histogram = macd - signal_line
            
            return {
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram
            }
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {
                'macd': pd.Series(index=prices.index),
                'signal': pd.Series(index=prices.index),
                'histogram': pd.Series(index=prices.index)
            }
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        try:
            middle = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower
            }
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {
                'upper': pd.Series(index=prices.index),
                'middle': pd.Series(index=prices.index),
                'lower': pd.Series(index=prices.index)
            }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR (Average True Range)"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            return atr
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series(index=df.index)

# Global instance
data_service = BinanceDataService() 