from enum import Enum
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StopLossType(Enum):
    FIXED_PERCENTAGE = "fixed_percentage"
    TRAILING_MAX_PRICE = "trailing_max_price"
    EMA_BASED = "ema_based"
    ATR_BASED = "atr_based"
    SUPPORT_LEVEL = "support_level"

@dataclass
class StopLossConfig:
    """Configuration for dynamic stop loss"""
    stop_loss_type: StopLossType
    percentage: float = 5.0  # For fixed percentage
    timeframe: str = "4h"    # For trailing stops
    ema_period: int = 7      # For EMA-based stops
    atr_period: int = 14     # For ATR-based stops
    atr_multiplier: float = 2.0  # For ATR-based stops
    support_lookback: int = 20   # For support level stops

class DynamicStopLoss:
    """Advanced dynamic stop loss system"""
    
    def __init__(self, config: StopLossConfig):
        self.config = config
        self.entry_price = None
        self.highest_price = None
        self.lowest_price = None
        self.entry_time = None
        self.position_side = None  # "long" or "short"
        
    def set_position(self, entry_price: float, side: str, entry_time: datetime):
        """Set the position details for stop loss calculation"""
        self.entry_price = entry_price
        self.highest_price = entry_price
        self.lowest_price = entry_price
        self.entry_time = entry_time
        self.position_side = side
        
    def update_price(self, current_price: float):
        """Update the current price and track highest/lowest"""
        if self.position_side == "long":
            self.highest_price = max(self.highest_price, current_price)
        elif self.position_side == "short":
            self.lowest_price = min(self.lowest_price, current_price)
            
    def calculate_stop_loss(self, market_data: pd.DataFrame) -> Optional[float]:
        """Calculate the current stop loss level based on the configured type"""
        if not self.entry_price or not self.position_side:
            return None
            
        try:
            if self.config.stop_loss_type == StopLossType.FIXED_PERCENTAGE:
                return self._calculate_fixed_percentage_stop()
            elif self.config.stop_loss_type == StopLossType.TRAILING_MAX_PRICE:
                return self._calculate_trailing_stop(market_data)
            elif self.config.stop_loss_type == StopLossType.EMA_BASED:
                return self._calculate_ema_stop(market_data)
            elif self.config.stop_loss_type == StopLossType.ATR_BASED:
                return self._calculate_atr_stop(market_data)
            elif self.config.stop_loss_type == StopLossType.SUPPORT_LEVEL:
                return self._calculate_support_stop(market_data)
            else:
                logger.warning(f"Unknown stop loss type: {self.config.stop_loss_type}")
                return None
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return None
    
    def _calculate_fixed_percentage_stop(self) -> float:
        """Calculate fixed percentage stop loss"""
        if self.position_side == "long":
            return self.entry_price * (1 - self.config.percentage / 100)
        else:  # short
            return self.entry_price * (1 + self.config.percentage / 100)
    
    def _calculate_trailing_stop(self, market_data: pd.DataFrame) -> float:
        """Calculate trailing stop based on max price on specified timeframe"""
        if not market_data.empty:
            # Get data from entry time onwards
            entry_time = pd.to_datetime(self.entry_time)
            recent_data = market_data[market_data.index >= entry_time]
            
            if not recent_data.empty:
                if self.position_side == "long":
                    max_price = recent_data['high'].max()
                    return max_price * (1 - self.config.percentage / 100)
                else:  # short
                    min_price = recent_data['low'].min()
                    return min_price * (1 + self.config.percentage / 100)
        
        # Fallback to fixed percentage if no data
        return self._calculate_fixed_percentage_stop()
    
    def _calculate_ema_stop(self, market_data: pd.DataFrame) -> float:
        """Calculate EMA-based stop loss"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        # Calculate EMA
        ema = market_data['close'].ewm(span=self.config.ema_period).mean()
        current_ema = ema.iloc[-1]
        
        if self.position_side == "long":
            # For long positions, stop loss is below EMA
            return current_ema * (1 - self.config.percentage / 100)
        else:  # short
            # For short positions, stop loss is above EMA
            return current_ema * (1 + self.config.percentage / 100)
    
    def _calculate_atr_stop(self, market_data: pd.DataFrame) -> float:
        """Calculate ATR-based stop loss"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        # Calculate ATR
        high_low = market_data['high'] - market_data['low']
        high_close = np.abs(market_data['high'] - market_data['close'].shift())
        low_close = np.abs(market_data['low'] - market_data['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=self.config.atr_period).mean()
        current_atr = atr.iloc[-1]
        current_price = market_data['close'].iloc[-1]
        
        if self.position_side == "long":
            return current_price - (current_atr * self.config.atr_multiplier)
        else:  # short
            return current_price + (current_atr * self.config.atr_multiplier)
    
    def _calculate_support_stop(self, market_data: pd.DataFrame) -> float:
        """Calculate support level stop loss"""
        if market_data.empty:
            return self._calculate_fixed_percentage_stop()
            
        # Find support levels using pivot points
        lookback = min(self.config.support_lookback, len(market_data))
        recent_data = market_data.tail(lookback)
        
        # Calculate pivot points
        pivot = (recent_data['high'].max() + recent_data['low'].min() + recent_data['close'].iloc[-1]) / 3
        support1 = (2 * pivot) - recent_data['high'].max()
        support2 = pivot - (recent_data['high'].max() - recent_data['low'].min())
        
        if self.position_side == "long":
            # Use the higher support level
            return max(support1, support2)
        else:  # short
            # For shorts, use resistance levels
            resistance1 = (2 * pivot) - recent_data['low'].min()
            resistance2 = pivot + (recent_data['high'].max() - recent_data['low'].min())
            return min(resistance1, resistance2)
    
    def should_stop_loss(self, current_price: float, market_data: pd.DataFrame) -> bool:
        """Check if stop loss should be triggered"""
        stop_loss_level = self.calculate_stop_loss(market_data)
        if stop_loss_level is None:
            return False
            
        if self.position_side == "long":
            return current_price <= stop_loss_level
        else:  # short
            return current_price >= stop_loss_level
    
    def get_stop_loss_info(self, current_price: float, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive stop loss information"""
        stop_loss_level = self.calculate_stop_loss(market_data)
        
        info = {
            "stop_loss_type": self.config.stop_loss_type.value,
            "entry_price": self.entry_price,
            "current_price": current_price,
            "position_side": self.position_side,
            "stop_loss_level": stop_loss_level,
            "distance_to_stop": None,
            "stop_loss_percentage": None,
            "should_trigger": False
        }
        
        if stop_loss_level:
            if self.position_side == "long":
                info["distance_to_stop"] = current_price - stop_loss_level
                info["stop_loss_percentage"] = ((current_price - stop_loss_level) / current_price) * 100
            else:  # short
                info["distance_to_stop"] = stop_loss_level - current_price
                info["stop_loss_percentage"] = ((stop_loss_level - current_price) / current_price) * 100
                
            info["should_trigger"] = self.should_stop_loss(current_price, market_data)
            
        return info

class StopLossManager:
    """Manages multiple stop loss strategies for a trading bot"""
    
    def __init__(self):
        self.stop_losses: Dict[str, DynamicStopLoss] = {}
        
    def add_stop_loss(self, name: str, config: StopLossConfig):
        """Add a stop loss strategy"""
        self.stop_losses[name] = DynamicStopLoss(config)
        
    def set_position(self, entry_price: float, side: str, entry_time: datetime):
        """Set position details for all stop losses"""
        for stop_loss in self.stop_losses.values():
            stop_loss.set_position(entry_price, side, entry_time)
            
    def update_price(self, current_price: float):
        """Update current price for all stop losses"""
        for stop_loss in self.stop_losses.values():
            stop_loss.update_price(current_price)
            
    def check_stop_losses(self, current_price: float, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Check all stop losses and return results"""
        results = {}
        triggered_stops = []
        
        for name, stop_loss in self.stop_losses.items():
            info = stop_loss.get_stop_loss_info(current_price, market_data)
            results[name] = info
            
            if info["should_trigger"]:
                triggered_stops.append(name)
                
        results["triggered_stops"] = triggered_stops
        results["any_triggered"] = len(triggered_stops) > 0
        
        return results 