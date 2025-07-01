"""
Grid Trading Strategy Service
Advanced grid trading implementation with multiple algorithms and risk management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from app.models.trading import Trade, Position, OrderStatus
from app.models.bot import Bot
from app.trading.data_service import data_service
from app.services.exchange_service import ExchangeService
from app.core.logging import get_logger
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import math

logger = get_logger(__name__)

class GridType(str, Enum):
    """Grid trading algorithm types"""
    ARITHMETIC = "arithmetic"           # Equal price intervals
    GEOMETRIC = "geometric"             # Percentage-based intervals
    DYNAMIC = "dynamic"                 # Volatility-based adaptation
    FIBONACCI = "fibonacci"             # Fibonacci sequence intervals
    BOLLINGER = "bollinger"            # Bollinger Band based
    SUPPORT_RESISTANCE = "support_resistance"  # Based on S/R levels

class GridState(str, Enum):
    """Grid operational states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    REBALANCING = "rebalancing"
    PAUSED = "paused"
    STOPPED = "stopped"

class GridDirection(str, Enum):
    """Grid trading directions"""
    LONG_ONLY = "long_only"           # Only buy orders (accumulate on dips)
    SHORT_ONLY = "short_only"         # Only sell orders (profit on rallies)
    NEUTRAL = "neutral"               # Both buy and sell orders

class GridTradingConfig:
    """Configuration for grid trading strategy"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        # Grid Type Configuration
        self.grid_type = GridType(config_dict.get('grid_type', GridType.ARITHMETIC))
        self.grid_direction = GridDirection(config_dict.get('grid_direction', GridDirection.NEUTRAL))
        
        # Grid Parameters
        self.grid_levels = config_dict.get('grid_levels', 10)  # Number of grid levels
        self.grid_spacing_percent = config_dict.get('grid_spacing_percent', 1.0)  # % between levels
        self.investment_per_grid = config_dict.get('investment_per_grid', 100.0)  # USDT per grid level
        
        # Price Range Configuration
        self.price_upper_limit = config_dict.get('price_upper_limit')  # Optional upper limit
        self.price_lower_limit = config_dict.get('price_lower_limit')  # Optional lower limit
        self.auto_calculate_range = config_dict.get('auto_calculate_range', True)
        
        # Dynamic Grid Parameters
        self.volatility_lookback = config_dict.get('volatility_lookback', 20)  # Days for volatility calc
        self.volatility_multiplier = config_dict.get('volatility_multiplier', 2.0)
        self.rebalance_threshold = config_dict.get('rebalance_threshold', 0.1)  # 10% price move threshold
        
        # Risk Management
        self.max_total_investment = config_dict.get('max_total_investment', 1000.0)
        self.stop_loss_percent = config_dict.get('stop_loss_percent', 15.0)  # Stop entire grid
        self.take_profit_percent = config_dict.get('take_profit_percent', 25.0)  # Take profit entire grid
        self.max_open_orders = config_dict.get('max_open_orders', 20)
        
        # Fibonacci specific (if grid_type is FIBONACCI)
        self.fibonacci_base_spacing = config_dict.get('fibonacci_base_spacing', 0.5)
        
        # Bollinger specific (if grid_type is BOLLINGER)
        self.bollinger_period = config_dict.get('bollinger_period', 20)
        self.bollinger_std_dev = config_dict.get('bollinger_std_dev', 2.0)

class GridLevel:
    """Individual grid level"""
    
    def __init__(self, price: float, level_type: str, order_id: str = None):
        self.price = price
        self.level_type = level_type  # 'buy' or 'sell'
        self.order_id = order_id
        self.is_filled = False
        self.fill_time = None
        self.quantity = 0.0
        self.created_at = datetime.utcnow()

class GridTradingService:
    """
    Advanced Grid Trading Strategy Service
    
    Features:
    - Multiple grid algorithms (Arithmetic, Geometric, Dynamic, Fibonacci, Bollinger, S/R)
    - Intelligent grid management and rebalancing
    - Risk management with stop loss and take profit
    - Market condition adaptation
    - Performance tracking and optimization
    """

    def __init__(self, db: Session, bot: Bot, exchange_service: ExchangeService):
        self.db = db
        self.bot = bot
        self.exchange_service = exchange_service
        self.config = GridTradingConfig(bot.strategy_params or {})
        
        # Initialize grid state
        self.grid_levels: List[GridLevel] = []
        self.grid_state = GridState.INITIALIZING
        self.base_price = 0.0
        self.current_price = 0.0
        self.total_profit = 0.0
        self.total_investment = 0.0
        
        # Performance tracking
        self.trades_executed = 0
        self.successful_cycles = 0
        self.last_rebalance_time = None
        
        # Market data cache
        self._market_data_cache = {}
        self._cache_expiry = datetime.utcnow()

    def initialize_grid(self, symbol: str) -> Dict[str, Any]:
        """Initialize the grid trading setup for a symbol"""
        logger.info(f"🔲 Initializing {self.config.grid_type.value} grid for {symbol}")
        
        try:
            # Get current market data
            market_data = self._get_market_data(symbol)
            if market_data.empty:
                return {"success": False, "error": "Insufficient market data"}
            
            current_price = market_data['close'].iloc[-1]
            self.current_price = current_price
            self.base_price = current_price
            
            # Calculate optimal price range
            price_range = self._calculate_price_range(market_data)
            
            # Generate grid levels based on selected algorithm
            grid_levels = self._generate_grid_levels(current_price, price_range)
            
            # Create initial grid orders
            order_results = self._create_initial_orders(symbol, grid_levels)
            
            # Update grid state
            self.grid_state = GridState.ACTIVE
            
            result = {
                "success": True,
                "grid_type": self.config.grid_type.value,
                "grid_levels": len(grid_levels),
                "base_price": current_price,
                "price_range": price_range,
                "orders_created": order_results['orders_created'],
                "total_investment": order_results['total_investment'],
                "message": f"Grid initialized with {len(grid_levels)} levels"
            }
            
            logger.info(f"✅ Grid initialized: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error initializing grid for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    def process_grid_orders(self, symbol: str) -> Dict[str, Any]:
        """Process grid trading logic for active orders"""
        if self.grid_state != GridState.ACTIVE:
            return {"success": False, "message": f"Grid not active, current state: {self.grid_state.value}"}
        
        try:
            # Get current market data
            market_data = self._get_market_data(symbol)
            if market_data.empty:
                return {"success": False, "error": "Insufficient market data"}
            
            current_price = market_data['close'].iloc[-1]
            self.current_price = current_price
            
            # Check for filled orders and create counter-orders
            filled_orders = self._check_filled_orders(symbol)
            
            # Create counter-orders for filled positions
            counter_orders = self._create_counter_orders(symbol, filled_orders)
            
            # Check if grid needs rebalancing
            rebalance_needed = self._check_rebalance_conditions(current_price)
            if rebalance_needed:
                rebalance_result = self._rebalance_grid(symbol, current_price)
                counter_orders['rebalanced'] = True
                counter_orders.update(rebalance_result)
            
            # Check stop loss and take profit conditions
            risk_check = self._check_risk_conditions(symbol, current_price)
            if risk_check['action_required']:
                counter_orders.update(risk_check)
            
            return {
                "success": True,
                "current_price": current_price,
                "filled_orders": len(filled_orders),
                "counter_orders_created": counter_orders.get('orders_created', 0),
                "grid_state": self.grid_state.value,
                "total_profit": self.total_profit,
                "details": counter_orders
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing grid orders for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    def _get_market_data(self, symbol: str, lookback_days: int = 50) -> pd.DataFrame:
        """Get market data with caching"""
        now = datetime.utcnow()
        
        # Check cache validity (5 minutes)
        if (symbol in self._market_data_cache and 
            now < self._cache_expiry):
            return self._market_data_cache[symbol]
        
        # Fetch fresh data
        market_data = data_service.get_market_data_for_strategy(
            symbol, '1h', lookback_periods=lookback_days * 24
        )
        
        # Cache the data
        self._market_data_cache[symbol] = market_data
        self._cache_expiry = now + timedelta(minutes=5)
        
        return market_data

    def _calculate_price_range(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate optimal price range for grid placement"""
        if self.config.price_upper_limit and self.config.price_lower_limit:
            return {
                'upper_limit': self.config.price_upper_limit,
                'lower_limit': self.config.price_lower_limit,
                'method': 'manual'
            }
        
        current_price = market_data['close'].iloc[-1]
        
        if self.config.grid_type == GridType.BOLLINGER:
            # Use Bollinger Bands for range
            bb_period = self.config.bollinger_period
            bb_std = self.config.bollinger_std_dev
            
            sma = market_data['close'].rolling(window=bb_period).mean().iloc[-1]
            std = market_data['close'].rolling(window=bb_period).std().iloc[-1]
            
            upper_limit = sma + (bb_std * std)
            lower_limit = sma - (bb_std * std)
            
        elif self.config.grid_type == GridType.DYNAMIC:
            # Use volatility-based range
            returns = market_data['close'].pct_change().dropna()
            volatility = returns.rolling(window=self.config.volatility_lookback).std().iloc[-1]
            
            # Calculate range based on volatility
            volatility_range = volatility * self.config.volatility_multiplier * current_price
            upper_limit = current_price + volatility_range
            lower_limit = current_price - volatility_range
            
        elif self.config.grid_type == GridType.SUPPORT_RESISTANCE:
            # Calculate support and resistance levels
            high_prices = market_data['high'].rolling(window=20).max()
            low_prices = market_data['low'].rolling(window=20).min()
            
            recent_high = high_prices.iloc[-10:].max()  # Resistance
            recent_low = low_prices.iloc[-10:].min()    # Support
            
            upper_limit = recent_high * 1.02  # 2% above resistance
            lower_limit = recent_low * 0.98   # 2% below support
            
        else:
            # Default: percentage-based range around current price
            range_percent = self.config.grid_spacing_percent * self.config.grid_levels / 2
            upper_limit = current_price * (1 + range_percent / 100)
            lower_limit = current_price * (1 - range_percent / 100)
        
        return {
            'upper_limit': upper_limit,
            'lower_limit': lower_limit,
            'method': self.config.grid_type.value,
            'current_price': current_price
        }

    def _generate_grid_levels(self, current_price: float, price_range: Dict[str, float]) -> List[GridLevel]:
        """Generate grid levels based on the selected algorithm"""
        upper_limit = price_range['upper_limit']
        lower_limit = price_range['lower_limit']
        
        grid_levels = []
        
        if self.config.grid_type == GridType.ARITHMETIC:
            # Equal price intervals
            price_step = (upper_limit - lower_limit) / (self.config.grid_levels - 1)
            
            for i in range(self.config.grid_levels):
                price = lower_limit + (i * price_step)
                level_type = 'buy' if price < current_price else 'sell'
                grid_levels.append(GridLevel(price, level_type))
                
        elif self.config.grid_type == GridType.GEOMETRIC:
            # Percentage-based intervals
            ratio = (upper_limit / lower_limit) ** (1 / (self.config.grid_levels - 1))
            
            for i in range(self.config.grid_levels):
                price = lower_limit * (ratio ** i)
                level_type = 'buy' if price < current_price else 'sell'
                grid_levels.append(GridLevel(price, level_type))
                
        elif self.config.grid_type == GridType.FIBONACCI:
            # Fibonacci sequence intervals
            fibonacci_sequence = self._generate_fibonacci_sequence(self.config.grid_levels)
            
            # Normalize fibonacci numbers to price range
            max_fib = max(fibonacci_sequence)
            
            for i, fib_num in enumerate(fibonacci_sequence):
                normalized_position = fib_num / max_fib
                price = lower_limit + (normalized_position * (upper_limit - lower_limit))
                level_type = 'buy' if price < current_price else 'sell'
                grid_levels.append(GridLevel(price, level_type))
                
        elif self.config.grid_type == GridType.DYNAMIC:
            # Volatility-adjusted intervals
            # More levels closer to current price, fewer at extremes
            center_weight = 0.6  # 60% of levels near center
            center_levels = int(self.config.grid_levels * center_weight)
            edge_levels = self.config.grid_levels - center_levels
            
            # Create center levels (tight spacing)
            center_range = current_price * 0.05  # 5% around current price
            center_step = (center_range * 2) / center_levels
            
            for i in range(center_levels):
                price = (current_price - center_range) + (i * center_step)
                level_type = 'buy' if price < current_price else 'sell'
                grid_levels.append(GridLevel(price, level_type))
            
            # Create edge levels (wider spacing)
            edge_levels_per_side = edge_levels // 2
            
            # Lower edge levels
            lower_step = (current_price - center_range - lower_limit) / edge_levels_per_side
            for i in range(edge_levels_per_side):
                price = lower_limit + (i * lower_step)
                grid_levels.append(GridLevel(price, 'buy'))
            
            # Upper edge levels
            upper_step = (upper_limit - current_price - center_range) / edge_levels_per_side
            for i in range(edge_levels_per_side):
                price = (current_price + center_range) + ((i + 1) * upper_step)
                grid_levels.append(GridLevel(price, 'sell'))
                
        else:
            # Default to arithmetic
            return self._generate_grid_levels(current_price, price_range)
        
        # Sort grid levels by price
        grid_levels.sort(key=lambda x: x.price)
        
        # Apply grid direction filter
        if self.config.grid_direction == GridDirection.LONG_ONLY:
            grid_levels = [level for level in grid_levels if level.level_type == 'buy']
        elif self.config.grid_direction == GridDirection.SHORT_ONLY:
            grid_levels = [level for level in grid_levels if level.level_type == 'sell']
        
        logger.info(f"🔲 Generated {len(grid_levels)} grid levels using {self.config.grid_type.value} algorithm")
        return grid_levels

    def _generate_fibonacci_sequence(self, length: int) -> List[int]:
        """Generate Fibonacci sequence of given length"""
        if length <= 0:
            return []
        elif length == 1:
            return [1]
        elif length == 2:
            return [1, 1]
        
        fib_sequence = [1, 1]
        for i in range(2, length):
            fib_sequence.append(fib_sequence[i-1] + fib_sequence[i-2])
        
        return fib_sequence

    def _create_initial_orders(self, symbol: str, grid_levels: List[GridLevel]) -> Dict[str, Any]:
        """Create initial grid orders"""
        orders_created = 0
        total_investment = 0.0
        errors = []
        
        for level in grid_levels:
            try:
                # Calculate order quantity
                quantity = self._calculate_order_quantity(symbol, level.price, level.level_type)
                
                if quantity <= 0:
                    continue
                
                # Create limit order
                order_result = self._place_grid_order(symbol, level, quantity)
                
                if order_result['success']:
                    level.order_id = order_result['order_id']
                    level.quantity = quantity
                    orders_created += 1
                    
                    if level.level_type == 'buy':
                        total_investment += level.price * quantity
                else:
                    errors.append(f"Failed to place {level.level_type} order at {level.price}: {order_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error creating order for level {level.price}: {e}")
                errors.append(str(e))
        
        self.grid_levels = grid_levels
        self.total_investment = total_investment
        
        return {
            'orders_created': orders_created,
            'total_investment': total_investment,
            'errors': errors,
            'grid_levels_count': len(grid_levels)
        }

    def _calculate_order_quantity(self, symbol: str, price: float, order_type: str) -> float:
        """Calculate appropriate order quantity for grid level"""
        try:
            # Base quantity from investment per grid
            base_quantity = self.config.investment_per_grid / price
            
            # Apply quantity filters and minimum order size
            # TODO: Get these from exchange info
            min_quantity = 0.001  # Minimum order size (should be fetched from exchange)
            quantity_precision = 3  # Decimal places (should be fetched from exchange)
            
            # Round to appropriate precision
            quantity = round(base_quantity, quantity_precision)
            
            # Ensure minimum quantity
            if quantity < min_quantity:
                quantity = min_quantity
            
            return quantity
            
        except Exception as e:
            logger.error(f"Error calculating order quantity: {e}")
            return 0.0

    def _place_grid_order(self, symbol: str, level: GridLevel, quantity: float) -> Dict[str, Any]:
        """Place a grid order on the exchange"""
        try:
            # Determine order side
            side = level.level_type  # 'buy' or 'sell'
            
            # Create trade record in database
            trade = Trade(
                user_id=self.bot.user_id,
                bot_id=self.bot.id,
                exchange_connection_id=self.bot.exchange_connection_id,
                symbol=symbol,
                trade_type=self.bot.trade_type,
                order_type='limit',
                side=side,
                quantity=quantity,
                price=level.price,
                status=OrderStatus.PENDING.value
            )
            
            self.db.add(trade)
            self.db.commit()
            
            # TODO: Integrate with actual exchange API
            # For now, simulate order placement
            order_id = f"grid_{side}_{level.price}_{datetime.utcnow().timestamp()}"
            
            # Update trade with order ID
            trade.exchange_order_id = order_id
            trade.status = OrderStatus.OPEN.value
            self.db.commit()
            
            logger.info(f"📋 Placed {side} order: {quantity} {symbol} at {level.price}")
            
            return {
                'success': True,
                'order_id': order_id,
                'trade_id': trade.id
            }
            
        except Exception as e:
            logger.error(f"Error placing grid order: {e}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    def _check_filled_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Check for filled grid orders"""
        filled_orders = []
        
        # Get recent trades for this bot and symbol
        recent_trades = self.db.query(Trade).filter(
            and_(
                Trade.bot_id == self.bot.id,
                Trade.symbol == symbol,
                Trade.status == OrderStatus.FILLED.value,
                Trade.executed_at >= datetime.utcnow() - timedelta(hours=1)  # Last hour
            )
        ).all()
        
        for trade in recent_trades:
            # Check if this trade corresponds to a grid level
            for level in self.grid_levels:
                if (level.order_id == trade.exchange_order_id and 
                    not level.is_filled):
                    
                    level.is_filled = True
                    level.fill_time = trade.executed_at
                    
                    filled_orders.append({
                        'trade': trade,
                        'level': level,
                        'price': trade.executed_price or trade.price,
                        'quantity': trade.quantity,
                        'side': trade.side
                    })
                    
                    logger.info(f"✅ Grid order filled: {trade.side} {trade.quantity} at {trade.executed_price}")
        
        return filled_orders

    def _create_counter_orders(self, symbol: str, filled_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create counter-orders for filled grid positions"""
        counter_orders_created = 0
        profit_realized = 0.0
        
        for filled_order in filled_orders:
            try:
                trade = filled_order['trade']
                level = filled_order['level']
                
                # Calculate counter-order price
                if trade.side == 'buy':
                    # Bought at grid level, now place sell order above
                    counter_price = level.price * (1 + self.config.grid_spacing_percent / 100)
                    counter_side = 'sell'
                else:
                    # Sold at grid level, now place buy order below
                    counter_price = level.price * (1 - self.config.grid_spacing_percent / 100)
                    counter_side = 'buy'
                
                # Create counter-order
                counter_level = GridLevel(counter_price, counter_side)
                order_result = self._place_grid_order(symbol, counter_level, trade.quantity)
                
                if order_result['success']:
                    counter_level.order_id = order_result['order_id']
                    self.grid_levels.append(counter_level)
                    counter_orders_created += 1
                    
                    # Calculate profit (if applicable)
                    if trade.side == 'sell':
                        # This was a profitable sell
                        original_buy_price = level.price * (1 - self.config.grid_spacing_percent / 100)
                        profit_per_unit = level.price - original_buy_price
                        profit_realized += profit_per_unit * trade.quantity
                        
                        logger.info(f"💰 Grid profit realized: ${profit_realized:.2f}")
                
            except Exception as e:
                logger.error(f"Error creating counter-order: {e}")
        
        self.total_profit += profit_realized
        self.trades_executed += len(filled_orders)
        
        return {
            'orders_created': counter_orders_created,
            'profit_realized': profit_realized,
            'total_profit': self.total_profit
        }

    def _check_rebalance_conditions(self, current_price: float) -> bool:
        """Check if grid needs rebalancing"""
        if not self.base_price:
            return False
        
        # Calculate price deviation from base price
        price_deviation = abs(current_price - self.base_price) / self.base_price
        
        # Check if deviation exceeds threshold
        if price_deviation > self.config.rebalance_threshold:
            logger.info(f"🔄 Grid rebalance needed: {price_deviation:.1%} deviation from base price")
            return True
        
        # Check time-based rebalancing (every 24 hours)
        if (self.last_rebalance_time and 
            datetime.utcnow() - self.last_rebalance_time > timedelta(hours=24)):
            logger.info(f"🔄 Grid rebalance needed: 24 hours since last rebalance")
            return True
        
        return False

    def _rebalance_grid(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Rebalance the grid around new price level"""
        logger.info(f"🔄 Rebalancing grid for {symbol} around new price: {current_price}")
        
        try:
            self.grid_state = GridState.REBALANCING
            
            # Cancel existing unfilled orders
            cancelled_orders = self._cancel_open_orders(symbol)
            
            # Update base price
            self.base_price = current_price
            
            # Get updated market data for new range calculation
            market_data = self._get_market_data(symbol)
            price_range = self._calculate_price_range(market_data)
            
            # Generate new grid levels
            new_grid_levels = self._generate_grid_levels(current_price, price_range)
            
            # Create new orders
            order_results = self._create_initial_orders(symbol, new_grid_levels)
            
            # Update state
            self.grid_state = GridState.ACTIVE
            self.last_rebalance_time = datetime.utcnow()
            
            return {
                'cancelled_orders': cancelled_orders,
                'new_orders_created': order_results['orders_created'],
                'new_base_price': current_price,
                'rebalance_time': self.last_rebalance_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error rebalancing grid: {e}")
            self.grid_state = GridState.ACTIVE  # Restore previous state
            return {'error': str(e)}

    def _cancel_open_orders(self, symbol: str) -> int:
        """Cancel all open grid orders"""
        cancelled_count = 0
        
        # Get open orders for this bot and symbol
        open_trades = self.db.query(Trade).filter(
            and_(
                Trade.bot_id == self.bot.id,
                Trade.symbol == symbol,
                Trade.status == OrderStatus.OPEN.value
            )
        ).all()
        
        for trade in open_trades:
            try:
                # TODO: Cancel order on exchange
                # For now, just update status in database
                trade.status = OrderStatus.CANCELLED.value
                cancelled_count += 1
                
                # Remove from grid levels
                self.grid_levels = [
                    level for level in self.grid_levels 
                    if level.order_id != trade.exchange_order_id
                ]
                
            except Exception as e:
                logger.error(f"Error cancelling order {trade.exchange_order_id}: {e}")
        
        self.db.commit()
        logger.info(f"📋 Cancelled {cancelled_count} open orders")
        return cancelled_count

    def _check_risk_conditions(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Check stop loss and take profit conditions"""
        result = {'action_required': False}
        
        if not self.base_price:
            return result
        
        # Calculate overall P&L
        price_change_percent = (current_price - self.base_price) / self.base_price * 100
        
        # Check stop loss condition
        if abs(price_change_percent) >= self.config.stop_loss_percent:
            logger.warning(f"🛑 Stop loss triggered: {price_change_percent:.1f}% price change")
            
            # Stop entire grid
            stop_result = self._stop_grid(symbol, "stop_loss_triggered")
            result.update(stop_result)
            result['action_required'] = True
            result['trigger'] = 'stop_loss'
            
        # Check take profit condition
        elif self.total_profit >= (self.total_investment * self.config.take_profit_percent / 100):
            logger.info(f"🎯 Take profit triggered: ${self.total_profit:.2f} profit")
            
            # Stop entire grid and realize profits
            profit_result = self._stop_grid(symbol, "take_profit_triggered")
            result.update(profit_result)
            result['action_required'] = True
            result['trigger'] = 'take_profit'
        
        return result

    def _stop_grid(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Stop the entire grid trading operation"""
        logger.info(f"🛑 Stopping grid for {symbol}, reason: {reason}")
        
        try:
            # Cancel all open orders
            cancelled_orders = self._cancel_open_orders(symbol)
            
            # Close all open positions (if any)
            closed_positions = self._close_open_positions(symbol)
            
            # Update grid state
            self.grid_state = GridState.STOPPED
            
            # Log final statistics
            final_stats = {
                'reason': reason,
                'cancelled_orders': cancelled_orders,
                'closed_positions': closed_positions,
                'total_profit': self.total_profit,
                'total_investment': self.total_investment,
                'trades_executed': self.trades_executed,
                'successful_cycles': self.successful_cycles,
                'final_state': self.grid_state.value
            }
            
            logger.info(f"📊 Grid stopped - Final stats: {final_stats}")
            return final_stats
            
        except Exception as e:
            logger.error(f"❌ Error stopping grid: {e}")
            return {'error': str(e)}

    def _close_open_positions(self, symbol: str) -> int:
        """Close any open positions related to this grid"""
        closed_count = 0
        
        # Get open positions for this bot and symbol
        open_positions = self.db.query(Position).filter(
            and_(
                Position.bot_id == self.bot.id,
                Position.symbol == symbol,
                Position.is_open == True
            )
        ).all()
        
        for position in open_positions:
            try:
                # TODO: Place market order to close position
                # For now, just mark as closed
                position.is_open = False
                position.closed_at = datetime.utcnow()
                closed_count += 1
                
            except Exception as e:
                logger.error(f"Error closing position {position.id}: {e}")
        
        self.db.commit()
        return closed_count

    def get_grid_status(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive grid trading status"""
        try:
            # Get current market data
            market_data = self._get_market_data(symbol)
            current_price = market_data['close'].iloc[-1] if not market_data.empty else 0.0
            
            # Count grid level status
            total_levels = len(self.grid_levels)
            filled_levels = len([level for level in self.grid_levels if level.is_filled])
            open_orders = total_levels - filled_levels
            
            # Calculate performance metrics
            unrealized_pnl = self._calculate_unrealized_pnl(current_price)
            total_pnl = self.total_profit + unrealized_pnl
            roi_percent = (total_pnl / self.total_investment * 100) if self.total_investment > 0 else 0.0
            
            status = {
                'symbol': symbol,
                'grid_state': self.grid_state.value,
                'grid_type': self.config.grid_type.value,
                'grid_direction': self.config.grid_direction.value,
                'current_price': current_price,
                'base_price': self.base_price,
                'price_change_percent': ((current_price - self.base_price) / self.base_price * 100) if self.base_price > 0 else 0.0,
                
                # Grid statistics
                'total_grid_levels': total_levels,
                'filled_levels': filled_levels,
                'open_orders': open_orders,
                'trades_executed': self.trades_executed,
                'successful_cycles': self.successful_cycles,
                
                # Financial metrics
                'total_investment': self.total_investment,
                'realized_profit': self.total_profit,
                'unrealized_pnl': unrealized_pnl,
                'total_pnl': total_pnl,
                'roi_percent': roi_percent,
                
                # Risk metrics
                'max_investment_used': (self.total_investment / self.config.max_total_investment * 100) if self.config.max_total_investment > 0 else 0.0,
                'stop_loss_level': self.base_price * (1 - self.config.stop_loss_percent / 100) if self.base_price > 0 else 0.0,
                'take_profit_level': self.config.take_profit_percent,
                
                # Timestamps
                'last_rebalance_time': self.last_rebalance_time,
                'grid_uptime': (datetime.utcnow() - (self.last_rebalance_time or datetime.utcnow())).total_seconds() / 3600,  # hours
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting grid status: {e}")
            return {'error': str(e)}

    def _calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L from open positions"""
        unrealized_pnl = 0.0
        
        # Get open positions
        open_positions = self.db.query(Position).filter(
            and_(
                Position.bot_id == self.bot.id,
                Position.is_open == True
            )
        ).all()
        
        for position in open_positions:
            if position.side == 'buy':
                # Long position: profit when price goes up
                pnl = (current_price - position.entry_price) * position.quantity
            else:
                # Short position: profit when price goes down
                pnl = (position.entry_price - current_price) * position.quantity
            
            unrealized_pnl += pnl
        
        return unrealized_pnl

    def get_optimization_suggestions(self, symbol: str) -> Dict[str, Any]:
        """Analyze performance and suggest optimizations"""
        try:
            status = self.get_grid_status(symbol)
            suggestions = []
            
            # Analyze grid performance
            if status['trades_executed'] > 10:  # Enough data for analysis
                success_rate = status['successful_cycles'] / status['trades_executed'] * 100
                
                if success_rate < 70:
                    suggestions.append({
                        'type': 'grid_spacing',
                        'message': 'Consider increasing grid spacing to capture larger price movements',
                        'current_spacing': self.config.grid_spacing_percent,
                        'suggested_spacing': self.config.grid_spacing_percent * 1.2
                    })
                
                if status['roi_percent'] < 5 and status['grid_uptime'] > 24:  # Less than 5% ROI in 24+ hours
                    suggestions.append({
                        'type': 'investment_per_grid',
                        'message': 'Consider increasing investment per grid level for higher returns',
                        'current_investment': self.config.investment_per_grid,
                        'suggested_investment': self.config.investment_per_grid * 1.5
                    })
                
                # Check if grid needs more levels
                if status['open_orders'] < 3:
                    suggestions.append({
                        'type': 'grid_levels',
                        'message': 'Consider adding more grid levels for better market coverage',
                        'current_levels': self.config.grid_levels,
                        'suggested_levels': self.config.grid_levels + 5
                    })
            
            # Market condition analysis
            market_data = self._get_market_data(symbol)
            if not market_data.empty:
                # Calculate volatility
                returns = market_data['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(24)  # 24-hour volatility
                
                if volatility > 0.05:  # High volatility (>5%)
                    suggestions.append({
                        'type': 'volatility_adjustment',
                        'message': 'High volatility detected - consider dynamic grid or wider spacing',
                        'current_volatility': volatility,
                        'suggested_action': 'Switch to dynamic grid type'
                    })
                elif volatility < 0.01:  # Low volatility (<1%)
                    suggestions.append({
                        'type': 'volatility_adjustment',
                        'message': 'Low volatility detected - consider tighter grid spacing',
                        'current_volatility': volatility,
                        'suggested_action': 'Reduce grid spacing by 20%'
                    })
            
            return {
                'symbol': symbol,
                'analysis_time': datetime.utcnow(),
                'performance_metrics': status,
                'suggestions': suggestions,
                'optimization_score': len(suggestions)  # Fewer suggestions = better optimization
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization suggestions: {e}")
            return {'error': str(e)} 