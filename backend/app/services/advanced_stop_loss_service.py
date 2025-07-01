"""
Advanced Dynamic Stop Loss Service
Enhances the existing stop loss system with advanced algorithms and real-time management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import asyncio

from app.models.trading import Trade, Position, OrderStatus
from app.models.user import User
from app.models.bot import Bot
from app.models.exchange import ExchangeConnection
from app.trading.stop_loss import StopLossType, StopLossConfig, DynamicStopLoss
from app.trading.data_service import data_service
from app.trading.trading_service import trading_service
from app.services.stop_loss_timeout_handler import safe_dynamic_stoploss_update
from app.services.activity_service import ActivityService, ActivityCreate
from app.core.logging import get_logger

logger = get_logger(__name__)

class AdvancedStopLossType(Enum):
    """Extended stop loss types with advanced algorithms"""
    # Existing types
    FIXED_PERCENTAGE = "fixed_percentage"
    TRAILING_MAX_PRICE = "trailing_max_price" 
    EMA_BASED = "ema_based"
    ATR_BASED = "atr_based"
    SUPPORT_LEVEL = "support_level"
    
    # Advanced types
    ADAPTIVE_ATR = "adaptive_atr"
    VOLATILITY_BASED = "volatility_based"
    FIBONACCI_RETRACEMENT = "fibonacci_retracement"
    SUPERTREND = "supertrend"
    PARABOLIC_SAR = "parabolic_sar"
    BOLLINGER_BAND = "bollinger_band"
    RISK_REWARD_RATIO = "risk_reward_ratio"
    TIME_DECAY = "time_decay"
    MOMENTUM_DIVERGENCE = "momentum_divergence"

@dataclass
class AdvancedStopLossConfig:
    """Enhanced configuration for advanced stop loss algorithms"""
    stop_loss_type: AdvancedStopLossType
    percentage: float = 5.0
    timeframe: str = "4h"
    
    # EMA/MA parameters
    ema_period: int = 7
    ema_fast: int = 12
    ema_slow: int = 26
    
    # ATR parameters
    atr_period: int = 14
    atr_multiplier: float = 2.0
    adaptive_atr_lookback: int = 50
    
    # Volatility parameters
    volatility_period: int = 20
    volatility_multiplier: float = 2.0
    
    # Support/Resistance parameters
    support_lookback: int = 20
    fibonacci_lookback: int = 100
    
    # SuperTrend parameters
    supertrend_period: int = 10
    supertrend_multiplier: float = 3.0
    
    # Parabolic SAR parameters
    sar_acceleration: float = 0.02
    sar_maximum: float = 0.2
    
    # Bollinger Band parameters
    bb_period: int = 20
    bb_std_dev: float = 2.0
    
    # Risk/Reward parameters
    risk_reward_ratio: float = 1.5
    max_risk_percent: float = 2.0
    
    # Time decay parameters
    time_decay_hours: int = 24
    time_decay_factor: float = 0.1
    
    # Momentum parameters
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70

class AdvancedDynamicStopLoss(DynamicStopLoss):
    """Enhanced dynamic stop loss with advanced algorithms"""
    
    def __init__(self, config: AdvancedStopLossConfig):
        # Convert to base config for parent initialization
        base_config = StopLossConfig(
            stop_loss_type=StopLossType(config.stop_loss_type.value) if config.stop_loss_type.value in [t.value for t in StopLossType] else StopLossType.FIXED_PERCENTAGE,
            percentage=config.percentage,
            timeframe=config.timeframe,
            ema_period=config.ema_period,
            atr_period=config.atr_period,
            atr_multiplier=config.atr_multiplier,
            support_lookback=config.support_lookback
        )
        super().__init__(base_config)
        self.advanced_config = config
        self.sar_af = config.sar_acceleration
        self.sar_ep = None  # Extreme point
        self.trend_direction = None
        
    def calculate_advanced_stop_loss(self, market_data: pd.DataFrame) -> Optional[float]:
        """Calculate stop loss using advanced algorithms"""
        if not self.entry_price or not self.position_side:
            return None
            
        try:
            if self.advanced_config.stop_loss_type == AdvancedStopLossType.ADAPTIVE_ATR:
                return self._calculate_adaptive_atr_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.VOLATILITY_BASED:
                return self._calculate_volatility_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.FIBONACCI_RETRACEMENT:
                return self._calculate_fibonacci_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.SUPERTREND:
                return self._calculate_supertrend_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.PARABOLIC_SAR:
                return self._calculate_parabolic_sar_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.BOLLINGER_BAND:
                return self._calculate_bollinger_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.RISK_REWARD_RATIO:
                return self._calculate_risk_reward_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.TIME_DECAY:
                return self._calculate_time_decay_stop(market_data)
            elif self.advanced_config.stop_loss_type == AdvancedStopLossType.MOMENTUM_DIVERGENCE:
                return self._calculate_momentum_divergence_stop(market_data)
            else:
                # Fall back to base implementation
                return self.calculate_stop_loss(market_data)
                
        except Exception as e:
            logger.error(f"Error calculating advanced stop loss: {e}")
            return self._calculate_fixed_percentage_stop()
    
    def _calculate_adaptive_atr_stop(self, market_data: pd.DataFrame) -> float:
        """Adaptive ATR that adjusts multiplier based on market volatility"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        # Calculate ATR
        atr = self._calculate_atr(market_data)
        current_atr = atr.iloc[-1]
        current_price = market_data['close'].iloc[-1]
        
        # Calculate volatility trend over lookback period
        lookback = min(self.advanced_config.adaptive_atr_lookback, len(atr))
        recent_atr = atr.tail(lookback)
        atr_trend = (recent_atr.iloc[-1] - recent_atr.iloc[0]) / recent_atr.iloc[0]
        
        # Adapt multiplier based on volatility trend
        base_multiplier = self.advanced_config.atr_multiplier
        if atr_trend > 0.2:  # High volatility increasing
            multiplier = base_multiplier * 1.5
        elif atr_trend < -0.2:  # Volatility decreasing
            multiplier = base_multiplier * 0.7
        else:
            multiplier = base_multiplier
            
        if self.position_side == "long":
            return current_price - (current_atr * multiplier)
        else:
            return current_price + (current_atr * multiplier)
    
    def _calculate_volatility_stop(self, market_data: pd.DataFrame) -> float:
        """Stop loss based on price volatility and standard deviation"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        period = self.advanced_config.volatility_period
        multiplier = self.advanced_config.volatility_multiplier
        
        # Calculate rolling standard deviation
        price_std = market_data['close'].rolling(window=period).std()
        current_std = price_std.iloc[-1]
        current_price = market_data['close'].iloc[-1]
        
        if self.position_side == "long":
            return current_price - (current_std * multiplier)
        else:
            return current_price + (current_std * multiplier)
    
    def _calculate_fibonacci_stop(self, market_data: pd.DataFrame) -> float:
        """Stop loss based on Fibonacci retracement levels"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        lookback = min(self.advanced_config.fibonacci_lookback, len(market_data))
        recent_data = market_data.tail(lookback)
        
        high = recent_data['high'].max()
        low = recent_data['low'].min()
        range_size = high - low
        
        # Fibonacci levels
        fib_levels = {
            0.236: high - (range_size * 0.236),
            0.382: high - (range_size * 0.382),
            0.618: high - (range_size * 0.618),
            0.786: high - (range_size * 0.786)
        }
        
        current_price = market_data['close'].iloc[-1]
        
        if self.position_side == "long":
            # Use 38.2% retracement as stop for long positions
            return fib_levels[0.382]
        else:
            # For short positions, use resistance levels
            return high - (range_size * 0.382)
    
    def _calculate_supertrend_stop(self, market_data: pd.DataFrame) -> float:
        """SuperTrend indicator based stop loss"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        period = self.advanced_config.supertrend_period
        multiplier = self.advanced_config.supertrend_multiplier
        
        # Calculate ATR
        atr = self._calculate_atr(market_data, period)
        
        # Calculate basic upper and lower bands
        hl2 = (market_data['high'] + market_data['low']) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        # SuperTrend calculation
        supertrend = pd.Series(index=market_data.index, dtype=float)
        trend = pd.Series(index=market_data.index, dtype=int)
        
        for i in range(len(market_data)):
            if i == 0:
                supertrend.iloc[i] = lower_band.iloc[i]
                trend.iloc[i] = 1
            else:
                # Determine trend direction
                if market_data['close'].iloc[i] > supertrend.iloc[i-1]:
                    trend.iloc[i] = 1
                    supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    trend.iloc[i] = -1
                    supertrend.iloc[i] = upper_band.iloc[i]
        
        current_supertrend = supertrend.iloc[-1]
        current_trend = trend.iloc[-1]
        
        if self.position_side == "long":
            return current_supertrend if current_trend == 1 else self._calculate_fixed_percentage_stop()
        else:
            return current_supertrend if current_trend == -1 else self._calculate_fixed_percentage_stop()
    
    def _calculate_parabolic_sar_stop(self, market_data: pd.DataFrame) -> float:
        """Parabolic SAR based stop loss"""
        if market_data.empty or len(market_data) < 2:
            return self._calculate_fixed_percentage_stop()
            
        acceleration = self.advanced_config.sar_acceleration
        maximum = self.advanced_config.sar_maximum
        
        # Initialize
        if self.sar_ep is None:
            if self.position_side == "long":
                self.sar_ep = market_data['low'].iloc[0]
                self.trend_direction = 1
            else:
                self.sar_ep = market_data['high'].iloc[0]
                self.trend_direction = -1
        
        # Calculate SAR
        sar_values = []
        af = acceleration
        ep = self.sar_ep
        trend = self.trend_direction
        
        for i in range(len(market_data)):
            if i == 0:
                sar = market_data['low'].iloc[i] if trend == 1 else market_data['high'].iloc[i]
            else:
                # Update SAR
                sar = sar_values[-1] + af * (ep - sar_values[-1])
                
                # Check for trend reversal
                if trend == 1 and market_data['low'].iloc[i] < sar:
                    trend = -1
                    sar = ep
                    ep = market_data['low'].iloc[i]
                    af = acceleration
                elif trend == -1 and market_data['high'].iloc[i] > sar:
                    trend = 1
                    sar = ep
                    ep = market_data['high'].iloc[i]
                    af = acceleration
                else:
                    # Update extreme point and acceleration
                    if trend == 1 and market_data['high'].iloc[i] > ep:
                        ep = market_data['high'].iloc[i]
                        af = min(af + acceleration, maximum)
                    elif trend == -1 and market_data['low'].iloc[i] < ep:
                        ep = market_data['low'].iloc[i]
                        af = min(af + acceleration, maximum)
            
            sar_values.append(sar)
        
        return sar_values[-1]
    
    def _calculate_bollinger_stop(self, market_data: pd.DataFrame) -> float:
        """Bollinger Band based stop loss"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        period = self.advanced_config.bb_period
        std_dev = self.advanced_config.bb_std_dev
        
        # Calculate Bollinger Bands
        sma = market_data['close'].rolling(window=period).mean()
        std = market_data['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        if self.position_side == "long":
            return current_lower
        else:
            return current_upper
    
    def _calculate_risk_reward_stop(self, market_data: pd.DataFrame) -> float:
        """Risk/reward ratio based stop loss"""
        if not hasattr(self, 'take_profit_level') or not self.take_profit_level:
            return self._calculate_fixed_percentage_stop()
            
        risk_reward_ratio = self.advanced_config.risk_reward_ratio
        
        if self.position_side == "long":
            potential_profit = self.take_profit_level - self.entry_price
            acceptable_loss = potential_profit / risk_reward_ratio
            return self.entry_price - acceptable_loss
        else:
            potential_profit = self.entry_price - self.take_profit_level
            acceptable_loss = potential_profit / risk_reward_ratio
            return self.entry_price + acceptable_loss
    
    def _calculate_time_decay_stop(self, market_data: pd.DataFrame) -> float:
        """Time-based stop loss that tightens over time"""
        if not self.entry_time:
            return self._calculate_fixed_percentage_stop()
            
        hours_elapsed = (datetime.utcnow() - self.entry_time).total_seconds() / 3600
        decay_hours = self.advanced_config.time_decay_hours
        decay_factor = self.advanced_config.time_decay_factor
        
        # Calculate time-based tightening
        if hours_elapsed >= decay_hours:
            time_multiplier = 1 - decay_factor
        else:
            time_multiplier = 1 - (decay_factor * (hours_elapsed / decay_hours))
        
        # Apply to base percentage stop
        base_stop = self._calculate_fixed_percentage_stop()
        
        if self.position_side == "long":
            # Tighten stop loss (move it higher)
            return self.entry_price - ((self.entry_price - base_stop) * time_multiplier)
        else:
            # Tighten stop loss (move it lower)
            return self.entry_price + ((base_stop - self.entry_price) * time_multiplier)
    
    def _calculate_momentum_divergence_stop(self, market_data: pd.DataFrame) -> float:
        """Stop loss based on momentum divergence (RSI)"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        # Calculate RSI
        rsi = self._calculate_rsi(market_data, self.advanced_config.rsi_period)
        current_rsi = rsi.iloc[-1]
        
        # Adjust stop loss based on momentum
        base_stop = self._calculate_fixed_percentage_stop()
        
        if self.position_side == "long":
            if current_rsi < self.advanced_config.rsi_oversold:
                # RSI oversold, tighten stop loss
                return base_stop * 1.2  # Move stop 20% closer
            elif current_rsi > self.advanced_config.rsi_overbought:
                # RSI overbought, loosen stop loss
                return base_stop * 0.8  # Move stop 20% further
        else:
            if current_rsi > self.advanced_config.rsi_overbought:
                # RSI overbought, tighten stop loss
                return base_stop * 0.8
            elif current_rsi < self.advanced_config.rsi_oversold:
                # RSI oversold, loosen stop loss
                return base_stop * 1.2
        
        return base_stop
    
    def _calculate_atr(self, market_data: pd.DataFrame, period: Optional[int] = None) -> pd.Series:
        """Calculate Average True Range"""
        if period is None:
            period = self.advanced_config.atr_period
            
        high_low = market_data['high'] - market_data['low']
        high_close = np.abs(market_data['high'] - market_data['close'].shift())
        low_close = np.abs(market_data['low'] - market_data['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        return true_range.rolling(window=period).mean()
    
    def _calculate_rsi(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = market_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

class AdvancedStopLossService:
    """Advanced stop loss management service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.activity_service = ActivityService()
        
    async def update_advanced_stop_losses(self) -> Dict[str, Any]:
        """Update stop losses using advanced algorithms for all positions"""
        try:
            results = {
                'total_positions': 0,
                'updated_positions': 0,
                'errors': 0,
                'position_results': []
            }
            
            # Get all open positions with advanced stop loss configurations
            open_positions = self.db.query(Position).join(Trade).join(Bot).filter(
                and_(
                    Position.is_open == True,
                    Bot.stop_loss_type.in_([
                        'adaptive_atr', 'volatility_based', 'fibonacci_retracement',
                        'supertrend', 'parabolic_sar', 'bollinger_band',
                        'risk_reward_ratio', 'time_decay', 'momentum_divergence'
                    ])
                )
            ).all()
            
            results['total_positions'] = len(open_positions)
            
            for position in open_positions:
                try:
                    position_result = await self._update_position_advanced_stop_loss(position)
                    results['position_results'].append(position_result)
                    
                    if position_result.get('updated'):
                        results['updated_positions'] += 1
                    if position_result.get('error'):
                        results['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error updating advanced stop loss for position {position.id}: {e}")
                    results['errors'] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Error in advanced stop loss update: {e}")
            return {
                'total_positions': 0,
                'updated_positions': 0,
                'errors': 1,
                'error_message': str(e),
                'position_results': []
            }
    
    async def _update_position_advanced_stop_loss(self, position: Position) -> Dict[str, Any]:
        """Update advanced stop loss for a single position"""
        position_result = {
            'position_id': position.id,
            'symbol': position.symbol,
            'updated': False,
            'error': False,
            'stop_loss_type': None,
            'old_stop_loss': None,
            'new_stop_loss': None,
            'reason': None
        }
        
        try:
            # Get the associated trade and bot
            trade = self.db.query(Trade).filter(
                Trade.exchange_order_id == position.exchange_order_id
            ).first()
            
            if not trade:
                position_result['error'] = True
                position_result['reason'] = 'No associated trade found'
                return position_result
            
            bot = self.db.query(Bot).filter(Bot.id == trade.bot_id).first() if trade.bot_id else None
            
            if not bot:
                position_result['error'] = True
                position_result['reason'] = 'No associated bot found'
                return position_result
            
            # Create advanced stop loss configuration
            config = AdvancedStopLossConfig(
                stop_loss_type=AdvancedStopLossType(bot.stop_loss_type),
                percentage=bot.stop_loss_percentage or 5.0,
                timeframe=bot.stop_loss_timeframe or "4h",
                ema_period=bot.stop_loss_ema_period or 7,
                atr_period=bot.stop_loss_atr_period or 14,
                atr_multiplier=bot.stop_loss_atr_multiplier or 2.0,
                support_lookback=bot.stop_loss_support_lookback or 20
            )
            
            # Create advanced stop loss instance
            stop_loss = AdvancedDynamicStopLoss(config)
            stop_loss.set_position(
                entry_price=position.entry_price,
                side=position.side,
                entry_time=position.opened_at
            )
            
            # Get market data
            market_data = data_service.get_market_data_for_strategy(
                position.symbol, 
                config.timeframe, 
                lookback_periods=200
            )
            
            if market_data.empty:
                position_result['error'] = True
                position_result['reason'] = 'No market data available'
                return position_result
            
            # Calculate new stop loss
            new_stop_loss = stop_loss.calculate_advanced_stop_loss(market_data)
            
            if new_stop_loss is None:
                position_result['error'] = True
                position_result['reason'] = 'Failed to calculate stop loss'
                return position_result
            
            current_stop_loss = trade.stop_loss
            position_result['stop_loss_type'] = config.stop_loss_type.value
            position_result['old_stop_loss'] = current_stop_loss
            position_result['new_stop_loss'] = new_stop_loss
            
            # Only update if the new stop loss is better (for long: higher, for short: lower)
            should_update = False
            if position.side == 'buy' and (not current_stop_loss or new_stop_loss > current_stop_loss):
                should_update = True
            elif position.side == 'sell' and (not current_stop_loss or new_stop_loss < current_stop_loss):
                should_update = True
            
            if should_update:
                # Update the trade's stop loss
                trade.stop_loss = new_stop_loss
                self.db.commit()
                
                # Try to update stop loss on exchange
                try:
                    await self._update_exchange_stop_loss(trade, new_stop_loss, position)
                except Exception as e:
                    logger.warning(f"Failed to update stop loss on exchange: {e}")
                
                position_result['updated'] = True
                position_result['reason'] = f'Updated using {config.stop_loss_type.value} algorithm'
                
                # Log activity
                user = self.db.query(User).filter(User.id == trade.user_id).first()
                if user:
                    activity = ActivityCreate(
                        type="advanced_stop_loss_updated",
                        description=f"Advanced stop loss updated for {position.symbol}: {current_stop_loss:.6f} → {new_stop_loss:.6f} using {config.stop_loss_type.value}",
                        amount=None
                    )
                    self.activity_service.log_activity(self.db, user, activity, bot_id=bot.id)
                
                logger.info(f"Advanced stop loss updated for position {position.id}: {current_stop_loss} -> {new_stop_loss}")
            else:
                position_result['reason'] = 'New stop loss not better than current'
            
            return position_result
            
        except Exception as e:
            logger.error(f"Error updating advanced stop loss for position {position.id}: {e}")
            position_result['error'] = True
            position_result['reason'] = str(e)
            return position_result
    
    async def _update_exchange_stop_loss(self, trade: Trade, new_stop_loss: float, position: Position):
        """Update stop loss order on the exchange"""
        try:
            # Get exchange connection
            connection = self.db.query(ExchangeConnection).filter(
                ExchangeConnection.user_id == trade.user_id
            ).first()
            
            if not connection:
                raise Exception("No exchange connection found")
            
            # Get user
            user = self.db.query(User).filter(User.id == trade.user_id).first()
            if not user:
                raise Exception("User not found")
            
            # Get exchange instance
            exchange = await trading_service.get_exchange(connection.exchange_name)
            if not exchange:
                raise Exception("Failed to get exchange instance")
            
            # Define position function
            def get_position_func(symbol):
                return {'quantity': float(position.quantity)}
            
            # Use safe update function
            update_result = await safe_dynamic_stoploss_update(
                exchange=exchange,
                session=self.db,
                symbol=position.symbol,
                current_stop=trade.stop_loss or 0,
                new_ema_stop=new_stop_loss,
                user_id=trade.user_id,
                exchange_conn=connection,
                user=user,
                activity_service=self.activity_service,
                get_position_func=get_position_func
            )
            
            if not update_result.get('success'):
                raise Exception(update_result.get('reason', 'Unknown error'))
                
        except Exception as e:
            logger.error(f"Failed to update stop loss on exchange: {e}")
            raise 