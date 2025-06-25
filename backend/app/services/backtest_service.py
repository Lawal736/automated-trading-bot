import pandas as pd
from typing import Dict, Any, List
from app.core.logging import get_logger
from app.services.exchange_service import ExchangeService
from app.services.strategy_service import StrategyService, Signal
from app.schemas.backtest import BacktestResult, TradeResult, BacktestRequest
from datetime import date
import numpy as np

logger = get_logger(__name__)

def clean_float(value: float) -> float:
    """Converts NaN/inf/-inf to 0.0, otherwise returns the float."""
    if value is None or np.isnan(value) or np.isinf(value):
        return 0.0
    return float(value)

def clean_numpy_types(obj):
    """Recursively convert numpy types to Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {key: clean_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return clean_float(float(obj))
    elif isinstance(obj, np.ndarray):
        return clean_numpy_types(obj.tolist())
    elif pd.isna(obj):
        return None
    else:
        return obj

class BacktestService:
    def __init__(self, exchange_service: ExchangeService):
        self.exchange_service = exchange_service
        
    def run_backtest(
        self,
        request: BacktestRequest,
    ) -> BacktestResult:
        """
        Run a backtest for the given strategy and parameters.
        """
        try:
            logger.info(f"[DEBUG] Backtest received symbol: {request.symbol}")
            # Convert symbol to CCXT format (BTCUSDT -> BTC/USDT)
            ccxt_symbol = request.symbol
            if len(ccxt_symbol) > 4 and '/' not in ccxt_symbol:
                ccxt_symbol = ccxt_symbol[:-4] + '/' + ccxt_symbol[-4:]
            klines = self._get_historical_data(
                request.exchange_connection_id, ccxt_symbol, request.timeframe, request.start_date, request.end_date
            )
            
            logger.info(f"[DEBUG] Symbol: {ccxt_symbol}, Klines fetched: {len(klines)}")
            if not klines or len(klines) < 50: # Reduced for testing
                raise ValueError(f"Insufficient historical data for {request.symbol}")
            
            logger.info(f"[DEBUG] Symbol: {ccxt_symbol}, Klines returned: {len(klines)}, First kline: {klines[0] if klines else 'None'}")
            
            # Convert to DataFrame
            df = self._prepare_dataframe(klines)
            
            # Map new strategy name to the correct logic and ensure EMA params
            strategy_name = request.strategy_name
            strategy_params = request.strategy_params
            if strategy_name == 'cassava_trend_following':
                # Ensure all keys are EMA-based for backend logic
                strategy_params = {
                    'ema_fast': strategy_params.get('ema_fast', 10),
                    'ema_slow_buy': strategy_params.get('ema_slow_buy', 20),
                    'ema_slow_sell': strategy_params.get('ema_slow_sell', 15),
                    'ema_exit': strategy_params.get('ema_exit', 25),
                    'short_exit_ema': strategy_params.get('short_exit_ema', 5),
                    'dmi_length': strategy_params.get('dmi_length', 14),
                    'di_plus_buy': strategy_params.get('di_plus_buy_threshold', 25),
                    'di_plus_short': strategy_params.get('di_plus_sell_threshold', 16),
                }
            strategy_service = StrategyService(
                strategy_name=strategy_name,
                exchange_service=self.exchange_service,
                strategy_params=strategy_params
            )
            
            # Run backtest
            result = self._execute_backtest(
                df, strategy_service, request.initial_balance, request.start_date, request.end_date
            )
            
            logger.info(f"Backtest completed for {request.symbol}: {result.total_return:.2f}% return")
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)
            raise
    
    def _get_historical_data(
        self, 
        exchange_conn_id: int, 
        symbol: str, 
        timeframe: str,
        start_date: date,
        end_date: date
    ) -> List:
        """Get historical kline data for backtesting."""
        # This is a simplified implementation. A robust version would handle pagination
        # and ensure the date range is fully covered.
        limit = 1000 
        return self.exchange_service.get_historical_klines(
            exchange_conn_id=exchange_conn_id,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
    
    def _calculate_dmi_pinescript(self, df: pd.DataFrame, length: int = 14, adx_smoothing: int = 14):
        """
        Calculate DMI (+DI, -DI) and ADX using Pine Script logic (Wilder's smoothing).
        Adds columns: 'plus_di_ps', 'minus_di_ps', 'adx_ps' to the DataFrame.
        """
        high = df['high']
        low = df['low']
        close = df['close']

        up = high.diff()
        down = -low.diff()
        plusDM = np.where((up > down) & (up > 0), up, 0.0)
        minusDM = np.where((down > up) & (down > 0), down, 0.0)

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        def rma(series, period):
            # Wilder's smoothing (RMA)
            result = series.copy()
            result.iloc[:period] = np.nan
            result.iloc[period] = series.iloc[:period+1].mean()
            for i in range(period+1, len(series)):
                result.iloc[i] = (result.iloc[i-1] * (period - 1) + series.iloc[i]) / period
            return result

        trur = rma(tr, length)
        plus = 100 * rma(pd.Series(plusDM), length) / trur
        minus = 100 * rma(pd.Series(minusDM), length) / trur
        dx = 100 * (plus - minus).abs() / (plus + minus)
        adx = rma(dx, adx_smoothing)

        df['plus_di_ps'] = plus
        df['minus_di_ps'] = minus
        df['adx_ps'] = adx

    def _prepare_dataframe(self, klines: List) -> pd.DataFrame:
        """Convert klines data to DataFrame with indicators."""
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.astype({
            'open': float, 'high': float, 'low': float, 
            'close': float, 'volume': float
        })
        # Make timestamp timezone-aware (UTC) then remove timezone for date conversion
        df['date'] = df['timestamp'].dt.tz_localize('UTC').dt.date
        # Add Pine Script DMI/ADX columns
        self._calculate_dmi_pinescript(df)
        # Ensure Pine Script DMI/ADX columns are always present and appear first
        pine_cols = ['plus_di_ps', 'minus_di_ps', 'adx_ps']
        for col in pine_cols:
            if col not in df.columns:
                df[col] = np.nan
        # Reorder columns to put Pine Script columns first (optional, for visibility)
        cols = pine_cols + [c for c in df.columns if c not in pine_cols]
        df = df[cols]
        # Clean up dataframe for serialization
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        indicator_data = df.where(pd.notnull(df), None).to_dict(orient='records')
        # Debug: Log the first row of indicator_data to verify columns
        if indicator_data:
            logger.info(f"First row of indicator_data: {indicator_data[0]}")
        return df
    
    def _execute_backtest(
        self, 
        df: pd.DataFrame, 
        strategy_service: StrategyService, 
        initial_balance: float,
        start_date: date,
        end_date: date
    ) -> BacktestResult:
        """Execute the backtest simulation."""
        balance = initial_balance
        position_size = 0.0
        entry_price = 0.0
        trades: List[TradeResult] = []
        equity_curve = [initial_balance]
        entry_condition_met = None  # Track if entry condition was met for the current open position
        current_position = None  # Track current position: 'LONG', 'SHORT', or None
        wait_long = None
        wait_short = None
        wait_long_idx = None
        wait_short_idx = None

        strategy_service._calculate_indicators(df)

        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            date = current['date'] if 'date' in current else current.name
            close = current['close']

            # Get signal and exit flag from strategy
            signal_result = strategy_service._check_signal(df, i)
            signal = signal_result['signal']
            condition_met = signal_result['condition_met']
            exit_long = signal_result.get('exit_long', False)
            exit_short = signal_result.get('exit_short', False)

            # Get max position size percent from strategy params (default 10%)
            max_position_size_percent = getattr(strategy_service, 'params', {}).get('max_position_size_percent', 10)
            max_position_size_dollars = balance * (max_position_size_percent / 100)

            # Entry logic
            if current_position is None:
                if signal == Signal.BUY and condition_met:
                    current_position = 'LONG'
                    entry_price = close
                    # Cap position size to max % of balance
                    position_size = max_position_size_dollars / entry_price
                    entry_condition_met = True
                    trades.append(TradeResult(
                        entry_date=date,
                        entry_price=entry_price,
                        exit_date=None,
                        exit_price=None,
                        pnl=0.0,  # Will be updated on exit
                        pnl_percent=0.0,  # Will be updated on exit
                        side='LONG',
                        condition_met=True
                    ))
                    logger.info({"event": "TRADE ENTRY: LONG", "date": str(date), "price": close, "position_size": position_size})
                elif signal == Signal.SELL and condition_met:
                    current_position = 'SHORT'
                    entry_price = close
                    # Cap position size to max % of balance
                    position_size = max_position_size_dollars / entry_price
                    entry_condition_met = True
                    trades.append(TradeResult(
                        entry_date=date,
                        entry_price=entry_price,
                        exit_date=None,
                        exit_price=None,
                        pnl=0.0,  # Will be updated on exit
                        pnl_percent=0.0,  # Will be updated on exit
                        side='SHORT',
                        condition_met=True
                    ))
                    logger.info({"event": "TRADE ENTRY: SHORT", "date": str(date), "price": close, "position_size": position_size})
            else:
                # Exit logic for long
                if current_position == 'LONG' and exit_long:
                    pnl_percent = ((close - entry_price) / entry_price) * 100
                    pnl_dollars = (close - entry_price) * position_size
                    pnl_percent = max(min(pnl_percent, 1000.0), -1000.0)
                    trades[-1].exit_date = date
                    trades[-1].exit_price = close
                    trades[-1].pnl = pnl_dollars
                    trades[-1].pnl_percent = pnl_percent
                    balance += pnl_dollars
                    balance = max(balance, 0)  # Prevent negative balance
                    equity_curve.append(balance)
                    logger.info({"event": "TRADE EXIT: LONG", "date": str(date), "price": close, "pnl_dollars": pnl_dollars, "pnl_percent": pnl_percent})
                    current_position = None
                    entry_price = 0.0
                    position_size = 0.0
                    entry_condition_met = None
                # Exit logic for short
                elif current_position == 'SHORT' and exit_short:
                    pnl_percent = ((entry_price - close) / entry_price) * 100
                    pnl_dollars = (entry_price - close) * position_size
                    pnl_percent = max(min(pnl_percent, 1000.0), -1000.0)
                    trades[-1].exit_date = date
                    trades[-1].exit_price = close
                    trades[-1].pnl = pnl_dollars
                    trades[-1].pnl_percent = pnl_percent
                    balance += pnl_dollars
                    balance = max(balance, 0)  # Prevent negative balance
                    equity_curve.append(balance)
                    logger.info({"event": "TRADE EXIT: SHORT", "date": str(date), "price": close, "pnl_dollars": pnl_dollars, "pnl_percent": pnl_percent})
                    current_position = None
                    entry_price = 0.0
                    position_size = 0.0
                    entry_condition_met = None

        # Finalize open trades
        if current_position is not None:
            close = df.iloc[-1]['close']
            if current_position == 'LONG':
                pnl_percent = ((close - entry_price) / entry_price) * 100
                pnl_dollars = (close - entry_price) * position_size
            else:  # SHORT
                pnl_percent = ((entry_price - close) / entry_price) * 100
                pnl_dollars = (entry_price - close) * position_size
            
            # Ensure PnL is within reasonable bounds to prevent JSON serialization issues
            pnl_percent = max(min(pnl_percent, 1000.0), -1000.0)  # Cap at ±1000%
            
            trades[-1].exit_date = df.iloc[-1]['date'] if 'date' in df.iloc[-1] else df.iloc[-1].name
            trades[-1].exit_price = close
            trades[-1].pnl = pnl_dollars
            trades[-1].pnl_percent = pnl_percent
            balance += pnl_dollars
            balance = max(balance, 0)  # Prevent negative balance
            equity_curve.append(balance)
            logger.info({"event": "FINAL TRADE EXIT", "position": current_position, "date": str(trades[-1].exit_date), "price": close, "pnl_dollars": pnl_dollars, "pnl_percent": pnl_percent})

        # Calculate stats
        total_return = ((balance - initial_balance) / initial_balance) * 100
        total_return = max(min(total_return, 1000.0), -1000.0)  # Cap at ±1000%
        total_trades = len(trades)
        win_trades = [t for t in trades if t.pnl and t.pnl > 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0.0
        max_drawdown = 0.0
        peak = initial_balance
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd

        # Clean up any NaN or inf values
        total_return = float(total_return) if not (pd.isna(total_return) or np.isinf(total_return)) else 0.0
        win_rate = float(win_rate) if not (pd.isna(win_rate) or np.isinf(win_rate)) else 0.0
        max_drawdown = float(max_drawdown) if not (pd.isna(max_drawdown) or np.isinf(max_drawdown)) else 0.0

        logger.info({"event": "Backtest completed", "total_return": total_return, "total_trades": total_trades, "win_rate": win_rate, "max_drawdown": max_drawdown})

        # Clean indicator data for JSON serialization
        indicator_data = df.to_dict(orient='records')
        for record in indicator_data:
            for key, value in record.items():
                if isinstance(value, (float, int)):
                    if pd.isna(value) or np.isinf(value):
                        record[key] = None
                    else:
                        # Ensure reasonable bounds for JSON serialization
                        if isinstance(value, float):
                            record[key] = max(min(value, 1e6), -1e6)

        return BacktestResult(
            total_return=total_return,
            total_trades=total_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            start_date=start_date,
            end_date=end_date,
            trades=trades,
            indicator_data=indicator_data
        ) 