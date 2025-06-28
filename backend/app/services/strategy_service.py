import pandas as pd
import pandas_ta as ta
from app.core.logging import get_logger
from app.services.exchange_service import ExchangeService
from enum import Enum
from typing import Dict, Any
from datetime import datetime
import numpy as np

logger = get_logger(__name__)

class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class StrategyService:
    def __init__(self, strategy_name: str, exchange_service: ExchangeService, strategy_params: Dict[str, Any] = None):
        self.strategy_name = strategy_name
        self.exchange_service = exchange_service
        self.params = strategy_params or {}
        # Unified state for crossover events
        self.crossover_state = {'type': None, 'bar_index': -1}

    def generate_signal(self, symbol: str) -> Signal:
        """Main method to generate a trading signal for a given symbol."""
        # This method would be used for live trading.
        # For backtesting, we call _check_signal directly.
        # Implementation for live trading would fetch data and then call _check_signal.
        return Signal.HOLD

    def generate_signal(self, symbol: str) -> Signal:
        """Main method to generate a trading signal for a given symbol."""
        try:
            # For live trading, we need to fetch current market data
            # This is a simplified implementation - in production you'd want to cache this data
            from app.trading.data_service import data_service
            
            # Fetch recent market data for signal generation
            # Use '1d' timeframe for Cassava strategy (daily candles)
            market_data = data_service.get_market_data_for_strategy(symbol, '1d', lookback_periods=100)
            
            if market_data.empty or len(market_data) < 50:
                logger.warning(f"Insufficient market data for {symbol}")
                return Signal.HOLD
            
            # Calculate indicators
            self._calculate_indicators(market_data)
            
            # Get the latest signal
            latest_signal = self._check_signal(market_data, len(market_data) - 1)
            
            return latest_signal['signal']
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return Signal.HOLD

    def _calculate_indicators(self, df: pd.DataFrame):
        """Calculates all necessary indicators for the strategy."""
        ema_fast_period = self.params.get('ema_fast', 10)
        ema_slow_buy_period = self.params.get('ema_slow_buy', 20)
        ema_slow_sell_period = self.params.get('ema_slow_sell', 15)
        ema_exit_period = self.params.get('ema_exit', 25)
        short_exit_ema_period = self.params.get('short_exit_ema', 5)
        dmi_length = self.params.get('dmi_length', 14)

        # Calculate all EMAs
        df[f"EMA_{ema_fast_period}"] = ta.ema(df['close'], length=ema_fast_period)
        df[f"EMA_{ema_slow_buy_period}"] = ta.ema(df['close'], length=ema_slow_buy_period)
        df[f"EMA_{ema_slow_sell_period}"] = ta.ema(df['close'], length=ema_slow_sell_period)
        df[f"EMA_{ema_exit_period}"] = ta.ema(df['close'], length=ema_exit_period)
        df[f"EMA_{short_exit_ema_period}"] = ta.ema(df['close'], length=short_exit_ema_period)
        df['EMA_8'] = ta.ema(df['close'], length=8)

        # Calculate fractal highs (pivot highs)
        lookback = 2  # 2 bars left/right for a 5-bar fractal
        df['fractal_high'] = df['high'][(df['high'].shift(lookback) < df['high']) & (df['high'].shift(-lookback) < df['high'])]
        df['fractal_high'] = df['fractal_high'].fillna(method='ffill')

        # Standard DMI calculation using pandas_ta adx function
        adx_result = ta.adx(df['high'], df['low'], df['close'], length=dmi_length)
        if adx_result is not None and not adx_result.empty:
            df[f'DMP_{dmi_length}'] = adx_result[f'DMP_{dmi_length}']
            df[f'DMN_{dmi_length}'] = adx_result[f'DMN_{dmi_length}']
            df[f'ADX_{dmi_length}'] = adx_result[f'ADX_{dmi_length}']

        # Custom Pine Script DMI/ADX Calculation
        pine_script_dmi = self.pine_script_dmi(df, length=dmi_length, pine_rma=True)
        df['plus_di_ps'] = pine_script_dmi['DI+']
        df['minus_di_ps'] = pine_script_dmi['DI-']
        df['adx_ps'] = pine_script_dmi['ADX']

    def _check_signal(self, df: pd.DataFrame, i: int) -> Dict[str, Any]:
        """Checks for a buy or sell signal at index i based on the defined strategy."""
        if i < 1:
            return {"signal": Signal.HOLD, "condition_met": False, "exit_long": False, "exit_short": False, "stop_loss_price": None}

        latest = df.iloc[i]
        previous = df.iloc[i-1]
        date = latest.name

        # Get column names from params
        ema_fast = f"EMA_{self.params.get('ema_fast', 10)}"
        ema_slow_buy = f"EMA_{self.params.get('ema_slow_buy', 20)}"
        ema_slow_sell = f"EMA_{self.params.get('ema_slow_sell', 15)}"
        ema_exit = f"EMA_{self.params.get('ema_exit', 25)}"
        short_exit_ema = f"EMA_{self.params.get('short_exit_ema', 5)}"
        ema8 = df['EMA_8']

        di_plus_buy_threshold = self.params.get('di_plus_buy', 25)
        di_plus_short_threshold = 16  # New strict threshold for short
        wait_bars_long = 10

        # Initialize outputs
        signal = Signal.HOLD
        condition_met = False
        exit_long = False
        exit_short = False
        stop_loss_price = None

        # --- Exit Conditions ---
        if latest['close'] < latest[ema_exit]:
            exit_long = True
        if latest['close'] > latest[short_exit_ema]:
            exit_short = True

        # --- Long Entry Logic (unchanged) ---
        long_crossover = previous[ema_fast] < previous[ema_slow_buy] and latest[ema_fast] > latest[ema_slow_buy]
        if latest[ema_fast] > latest[ema_slow_buy] and latest['plus_di_ps'] >= di_plus_buy_threshold:
            signal = Signal.BUY
            condition_met = True
            logger.info(f"[{date}] Cassava Trend Following LONG entry.")
            self.crossover_state = {'type': None, 'bar_index': -1}
            # --- EMA25-based stop loss for long ---
            # On entry, set stop loss at EMA25 (daily candle close)
            stop_loss_price = latest[ema_exit]  # EMA25
        else:
            # --- Pink Candle Short Entry Logic ---
            pink_candle_idx = None
            for j in range(i-1, -1, -1):
                row = df.iloc[j]
                if row[ema_fast] > row[ema_slow_buy] and row['close'] < ema8.iloc[j]:
                    pink_candle_idx = j
                    break
            if pink_candle_idx is not None and i == pink_candle_idx + 1:
                pink_low = df.iloc[pink_candle_idx]['low']
                if latest['close'] < pink_low and latest['plus_di_ps'] <= di_plus_short_threshold:
                    signal = Signal.SELL
                    condition_met = True
                    logger.info(f"[{date}] SHORT ENTRY: Close below pink candle wick and DI+ <= {di_plus_short_threshold}.")
                    # --- Fractal-based stop loss for short ---
                    # On entry, set stop loss at most recent fractal high
                    stop_loss_price = latest['fractal_high']

        # --- Long crossover/DI+ wait logic (unchanged) ---
        if not condition_met and long_crossover:
            self.crossover_state = {'type': 'LONG', 'bar_index': i}
            logger.info(f"[{date}] LONG CROSSOVER DETECTED at bar {i}")
        if self.crossover_state['type'] == 'LONG':
            bars_since = i - self.crossover_state['bar_index']
            if bars_since <= wait_bars_long:
                if latest['plus_di_ps'] >= di_plus_buy_threshold:
                    signal = Signal.BUY
                    condition_met = True
                    self.crossover_state = {'type': None, 'bar_index': -1}
            else:
                self.crossover_state = {'type': None, 'bar_index': -1}

        # --- Dynamic stop loss management for short trades ---
        # Only applies if currently in a short trade (handled by backtest/live logic)
        # If price closes above EMA8, exit immediately (soft stop)
        if signal == Signal.SELL or (condition_met and signal == Signal.HOLD):
            if latest['close'] > latest['EMA_8']:
                exit_short = True
                logger.info(f"[{date}] SHORT EXIT: Price closed above EMA8 (soft stop).")
            # If blue candle (EMA10 < EMA8 < EMA20), tighten stop to high of blue candle
            if latest[ema_fast] < latest['EMA_8'] < latest[ema_slow_buy]:
                stop_loss_price = latest['high']
                logger.info(f"[{date}] SHORT STOP LOSS TIGHTENED: Blue candle detected, stop loss set to high of blue candle.")
            # If a new fractal high forms, move stop to just above it
            if not pd.isna(latest['fractal_high']):
                stop_loss_price = latest['fractal_high']
                logger.info(f"[{date}] SHORT STOP LOSS TRAILED: New fractal high, stop loss moved to {stop_loss_price}.")

        # --- Dynamic stop loss management for long trades ---
        # Only applies if currently in a long trade (handled by backtest/live logic)
        if signal == Signal.BUY or (condition_met and signal == Signal.HOLD):
            # Trail the EMA25 stoploss for long positions
            if not pd.isna(latest[ema_exit]):
                stop_loss_price = latest[ema_exit]
                logger.info(f"[{date}] LONG STOP LOSS TRAILED: EMA25 stoploss updated to {stop_loss_price}.")

        return {
            "signal": signal,
            "condition_met": condition_met,
            "exit_long": exit_long,
            "exit_short": exit_short,
            "stop_loss_price": stop_loss_price
        }

    def pine_script_dmi(self, df, length=14, pine_rma=True):
        """Calculates DMI and ADX using a method similar to Pine Script's built-in functions."""
        df['tr'] = self.true_range(df['high'], df['low'], df['close'])
        up = df['high'].diff()
        down = -df['low'].diff()
        df['plus_dm'] = np.where((up > down) & (up > 0), up, 0.0)
        df['minus_dm'] = np.where((down > up) & (down > 0), down, 0.0)

        if pine_rma:
            df['smoothed_tr'] = df['tr'].ewm(alpha=1/length, adjust=False).mean()
            df['smoothed_plus_dm'] = df['plus_dm'].ewm(alpha=1/length, adjust=False).mean()
            df['smoothed_minus_dm'] = df['minus_dm'].ewm(alpha=1/length, adjust=False).mean()
        else:
            df['smoothed_tr'] = df['tr'].rolling(window=length).sum()
            df['smoothed_plus_dm'] = df['plus_dm'].rolling(window=length).sum()
            df['smoothed_minus_dm'] = df['minus_dm'].rolling(window=length).sum()

        df['di_plus'] = 100 * (df['smoothed_plus_dm'] / df['smoothed_tr'])
        df['di_minus'] = 100 * (df['smoothed_minus_dm'] / df['smoothed_tr'])
        df['dx'] = 100 * (abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus']))
        
        if pine_rma:
            df['adx'] = df['dx'].ewm(alpha=1/length, adjust=False).mean()
        else:
            df['adx'] = df['dx'].rolling(window=length).mean()

        return pd.DataFrame({
            'DI+': df['di_plus'],
            'DI-': df['di_minus'],
            'ADX': df['adx']
        })

    def true_range(self, high, low, close):
        """Calculates the True Range."""
        return pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
