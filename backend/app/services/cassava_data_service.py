from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from app.models.trading import CassavaTrendData
from app.services.strategy_service import StrategyService
from app.trading.data_service import data_service
from datetime import datetime, timedelta
import pandas as pd
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class CassavaDataService:
    def __init__(self, db: Session):
        self.db = db
        self.strategy_service = StrategyService(
            strategy_name='cassava_trend_following',
            exchange_service=None,  # Not needed for calculations
            strategy_params={
                'ema_fast': 10,
                'ema_slow_buy': 20,
                'ema_slow_sell': 15,
                'ema_exit': 25,
                'short_exit_ema': 5,
                'dmi_length': 14,
                'di_plus_buy': 25,
                'di_plus_short': 16,
            }
        )

    def get_trading_pairs(self) -> List[str]:
        """Get the trading pairs as used by the BOT and Manual Trade (from screenshot)"""
        return [
            "SUI/USDT", "ETH/USDT", "BTC/USDT", "XRP/USDT", "SOL/USDT", "BNB/USDT", "TRX/USDT", "DOGE/USDT", "ADA/USDT", "XLM/USDT", "BCH/USDT", "AVAX/USDT", "HBAR/USDT", "TON/USDT", "LTC/USDT", "AAVE/USDT", "UNI/USDT", "DOT/USDT", "ONDO/USDT", "TAO/USDT", "WLD/USDT", "APT/USDT", "ARB/USDT", "FET/USDT", "OP/USDT"
        ]

    def calculate_daily_cassava_data(self, symbol: str, date: datetime) -> Optional[CassavaTrendData]:
        """Calculate Cassava strategy data for a specific symbol and date"""
        try:
            # Get 60 days of daily data ending on the specified date (not current data)
            # This ensures we get historical data for that specific date
            end_date = date.replace(hour=23, minute=59, second=59)
            start_date = end_date - timedelta(days=70)  # Extra days for indicator calculation
            
            # Fetch historical market data ending on the specified date
            end_time_ms = int(end_date.timestamp() * 1000)
            market_data = data_service.get_market_data_for_strategy(
                symbol, '1d', lookback_periods=60, end_time=end_time_ms
            )
            
            if market_data.empty or len(market_data) < 50:
                logger.warning(f"Insufficient data for {symbol} on {date}")
                return None

            # Filter data to end on the specified date
            # Get the last 60 days of data up to the specified date
            market_data = market_data[market_data.index <= end_date].tail(60)
            
            if len(market_data) < 50:
                logger.warning(f"Insufficient historical data for {symbol} on {date}")
                return None

            # Calculate indicators using the strategy service
            self.strategy_service._calculate_indicators(market_data)
            
            # Get the latest data point (the specified date)
            latest_data = market_data.iloc[-1]
            
            # Extract technical indicators
            ema_10 = latest_data.get('EMA_10', 0)
            ema_8 = latest_data.get('EMA_8', 0)
            ema_20 = latest_data.get('EMA_20', 0)
            ema_15 = latest_data.get('EMA_15', 0)
            ema_25 = latest_data.get('EMA_25', 0)
            ema_5 = latest_data.get('EMA_5', 0)
            di_plus = latest_data.get('plus_di_ps', 0)
            top_fractal = latest_data.get('fractal_high', None)
            price = latest_data.get('close', None)
            
            # Determine trading condition
            trading_condition = self._determine_trading_condition(market_data, len(market_data) - 1)
            
            # Create CassavaTrendData object
            cassava_data = CassavaTrendData(
                date=date,
                symbol=symbol,
                ema_10=float(ema_10),
                ema_8=float(ema_8),
                ema_20=float(ema_20),
                ema_15=float(ema_15),
                ema_25=float(ema_25),
                ema_5=float(ema_5),
                di_plus=float(di_plus),
                top_fractal=float(top_fractal) if top_fractal and not pd.isna(top_fractal) else None,
                trading_condition=trading_condition,
                price=float(price) if price is not None else None
            )
            
            return cassava_data
            
        except Exception as e:
            logger.error(f"Error calculating Cassava data for {symbol} on {date}: {e}")
            return None

    def _determine_trading_condition(self, df: pd.DataFrame, i: int) -> str:
        """Determine trading condition (BUY/SHORT/HOLD) using Cassava strategy logic"""
        try:
            if i < 1:
                return "HOLD"
                
            latest = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Get column names
            ema_fast = 'EMA_10'
            ema_slow_buy = 'EMA_20'
            ema_slow_sell = 'EMA_15'
            ema_exit = 'EMA_25'
            short_exit_ema = 'EMA_5'
            ema8 = 'EMA_8'
            
            di_plus_buy_threshold = 25
            di_plus_short_threshold = 16
            
            # Check for BUY condition
            long_crossover = previous[ema_fast] < previous[ema_slow_buy] and latest[ema_fast] > latest[ema_slow_buy]
            if latest[ema_fast] > latest[ema_slow_buy] and latest['plus_di_ps'] >= di_plus_buy_threshold:
                return "BUY"
            
            # Check for SHORT condition (Pink candle logic)
            pink_candle_idx = None
            for j in range(i-1, -1, -1):
                row = df.iloc[j]
                if row[ema_fast] > row[ema_slow_buy] and row['close'] < row[ema8]:
                    pink_candle_idx = j
                    break
            if pink_candle_idx is not None and i == pink_candle_idx + 1:
                pink_low = df.iloc[pink_candle_idx]['low']
                if latest['close'] < pink_low and latest['plus_di_ps'] <= di_plus_short_threshold:
                    return "SHORT"
            
            # Check crossover wait logic
            if long_crossover:
                bars_since = i - (i-1)  # Simplified for daily data
                if bars_since <= 10 and latest['plus_di_ps'] >= di_plus_buy_threshold:
                    return "BUY"
            
            return "HOLD"
            
        except Exception as e:
            logger.error(f"Error determining trading condition: {e}")
            return "HOLD"

    def update_daily_data(self, date: datetime = None):
        """Update daily Cassava data for all trading pairs"""
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        trading_pairs = self.get_trading_pairs()
        logger.info(f"Updating Cassava data for {len(trading_pairs)} pairs on {date}")
        
        for symbol in trading_pairs:
            try:
                # Check if data already exists for this date and symbol
                existing_data = self.db.query(CassavaTrendData).filter(
                    and_(
                        CassavaTrendData.date == date,
                        CassavaTrendData.symbol == symbol
                    )
                ).first()
                
                if existing_data:
                    logger.info(f"Updating existing data for {symbol} on {date}")
                    cassava_data = self.calculate_daily_cassava_data(symbol, date)
                    if cassava_data:
                        existing_data.ema_10 = cassava_data.ema_10
                        existing_data.ema_8 = cassava_data.ema_8
                        existing_data.ema_20 = cassava_data.ema_20
                        existing_data.ema_15 = cassava_data.ema_15
                        existing_data.ema_25 = cassava_data.ema_25
                        existing_data.ema_5 = cassava_data.ema_5
                        existing_data.di_plus = cassava_data.di_plus
                        existing_data.top_fractal = cassava_data.top_fractal
                        existing_data.trading_condition = cassava_data.trading_condition
                        existing_data.price = cassava_data.price
                    continue
                
                # Calculate new data
                cassava_data = self.calculate_daily_cassava_data(symbol, date)
                if cassava_data:
                    self.db.add(cassava_data)
                    logger.info(f"Added Cassava data for {symbol}: {cassava_data.trading_condition}")
                
            except Exception as e:
                logger.error(f"Error updating data for {symbol}: {e}")
                continue
        
        # Commit all changes
        try:
            self.db.commit()
            logger.info(f"Successfully updated Cassava data for {date}")
        except Exception as e:
            logger.error(f"Error committing Cassava data: {e}")
            self.db.rollback()

    def cleanup_old_data(self):
        """Remove data older than 50 days (FIFO) - maintain exactly 50 days per symbol"""
        try:
            trading_pairs = self.get_trading_pairs()
            total_deleted = 0
            
            for symbol in trading_pairs:
                # Get all records for this symbol, ordered by date (oldest first)
                symbol_records = self.db.query(CassavaTrendData).filter(
                    CassavaTrendData.symbol == symbol
                ).order_by(CassavaTrendData.date).all()
                
                # If we have more than 50 records, delete the oldest ones
                if len(symbol_records) > 50:
                    records_to_delete = len(symbol_records) - 50
                    oldest_records = symbol_records[:records_to_delete]
                    
                    for record in oldest_records:
                        self.db.delete(record)
                    
                    total_deleted += records_to_delete
                    logger.info(f"Cleaned up {records_to_delete} old records for {symbol}")
            
            self.db.commit()
            logger.info(f"Cleaned up {total_deleted} total old Cassava trend data records")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            self.db.rollback()

    def get_records_count_per_symbol(self) -> dict:
        """Get the count of records per symbol for monitoring"""
        try:
            result = self.db.query(
                CassavaTrendData.symbol,
                func.count(CassavaTrendData.id).label('count')
            ).group_by(CassavaTrendData.symbol).all()
            
            return {symbol: count for symbol, count in result}
            
        except Exception as e:
            logger.error(f"Error getting records count per symbol: {e}")
            return {}

    def get_cassava_data(self, 
                        symbol: Optional[str] = None,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        trading_condition: Optional[str] = None,
                        page: int = 1,
                        size: int = 50) -> dict:
        """Get Cassava trend data with filtering and pagination"""
        try:
            query = self.db.query(CassavaTrendData)
            
            # Apply filters
            if symbol:
                query = query.filter(CassavaTrendData.symbol == symbol)
            if start_date:
                query = query.filter(CassavaTrendData.date >= start_date)
            if end_date:
                query = query.filter(CassavaTrendData.date <= end_date)
            if trading_condition:
                query = query.filter(CassavaTrendData.trading_condition == trading_condition)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * size
            data = query.order_by(desc(CassavaTrendData.date)).offset(offset).limit(size).all()
            
            return {
                "data": data,
                "total": total,
                "page": page,
                "size": size,
                "total_pages": (total + size - 1) // size
            }
            
        except Exception as e:
            logger.error(f"Error getting Cassava data: {e}")
            return {
                "data": [],
                "total": 0,
                "page": page,
                "size": size,
                "total_pages": 0
            } 