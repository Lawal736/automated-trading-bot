"use client";

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeftIcon,
  CogIcon,
  ShieldCheckIcon,
  CurrencyDollarIcon,
  BoltIcon,
  GlobeAltIcon,
  ClockIcon,
  BeakerIcon,
  PresentationChartLineIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { createBot } from '../../../lib/bots';
import { getExchanges, ExchangeConnection } from '../../../lib/exchanges';
import { useBacktestStore } from '../../../lib/store';
import TradingPairsSelect from '../../../components/TradingPairsSelect';

interface Strategy {
  id: string;
  name: string;
  description: string;
  risk: 'low' | 'medium' | 'high';
  minBalance: number;
}

const strategies: Strategy[] = [
  { id: 'cassava_trend_following', name: 'Cassava Trend Following Strategy', description: 'Follows market trends using EMAs, DMI, and advanced stop loss logic', risk: 'medium', minBalance: 1000 },
  { id: 'grid_trading', name: 'Grid Trading', description: 'Places buy and sell orders at regular price intervals with 6 advanced algorithms', risk: 'low', minBalance: 500 },
  { id: 'scalping', name: 'Scalping', description: 'Makes many small trades to capture small price movements', risk: 'high', minBalance: 2000 },
  { id: 'mean_reversion', name: 'Mean Reversion', description: 'Trades based on the assumption that prices will revert to their average', risk: 'medium', minBalance: 1500 },
  { id: 'arbitrage', name: 'Arbitrage', description: 'Exploits price differences between exchanges', risk: 'low', minBalance: 5000 }
];

const stopLossTypes = [
  { id: 'fixed_percentage', name: 'Fixed Percentage' },
  { id: 'trailing_max_price', name: 'Trailing Stop' },
  { id: 'ema_based', name: 'EMA Based' },
  { id: 'atr_based', name: 'ATR Based' },
  { id: 'support_level', name: 'Support Level' },
];

// Define the structure for the backtest result
// This should match the store's BacktestResult interface
interface BacktestResult {
  total_return: number;
  total_trades: number;
  win_rate: number;
  max_drawdown: number;
  start_date: string;
  end_date: string;
  trades: any[]; 
  indicator_data: any[];
}

export default function CreateBotPage() {
  const router = useRouter();
  const { setBacktestResult } = useBacktestStore();
  const [botName, setBotName] = useState('');
  const [exchangeConnections, setExchangeConnections] = useState<ExchangeConnection[]>([]);
  const [selectedExchange, setSelectedExchange] = useState<number | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  
  // Strategy-specific parameters
  const [strategyParams, setStrategyParams] = useState({
    // Cassava parameters
    ema_fast: 10,
    ema_slow_buy: 20,
    ema_slow_sell: 15,
    dmi_length: 14,
    di_plus_buy_threshold: 25,
    di_plus_sell_threshold: 19,
    timeframe: '4h',
    symbol: 'BTCUSDT',
    
    // Grid Trading parameters
    grid_type: 'arithmetic',
    grid_direction: 'neutral',
    grid_levels: 10,
    grid_spacing_percent: 1.0,
    investment_per_grid: 100,
    max_total_investment: 1000,
    volatility_lookback: 20,
    volatility_multiplier: 2.0,
    rebalance_threshold: 0.1,
    fibonacci_base_spacing: 0.5,
    bollinger_period: 20,
    bollinger_std_dev: 2.0,
    stop_loss_percent: 15,
    take_profit_percent: 25,
    max_open_orders: 20,
  });

  // Backtest state
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestResult, setLocalBacktestResult] = useState<BacktestResult | null>(null);

  // Trading Config
  const [tradeType, setTradeType] = useState<'spot' | 'futures'>('spot');
  const [leverage, setLeverage] = useState(1);
  const [direction, setDirection] = useState<'long' | 'short' | 'both'>('both');
  const [selectedPairs, setSelectedPairs] = useState<string[]>(['BTC/USDT']);
  
  // Risk Management
  const [initialBalance, setInitialBalance] = useState(1000);
  const [trade_interval_seconds, setTradeIntervalSeconds] = useState(60);
  const [max_position_size_percent, setMaxPositionSizePercent] = useState(10);
  const [max_trades_per_day, setMaxTradesPerDay] = useState<number | null>(null);
  const [min_balance_threshold, setMinBalanceThreshold] = useState<number | null>(null);
  const [max_daily_loss, setMaxDailyLoss] = useState<number | null>(null);
  
  // Advanced Stop Loss
  const [stop_loss_type, setStopLossType] = useState('fixed_percentage');
  const [stop_loss_percentage, setStopLossPercentage] = useState(5);
  const [stop_loss_timeframe, setStopLossTimeframe] = useState('4h');
  const [stop_loss_ema_period, setStopLossEmaPeriod] = useState(7);
  const [stop_loss_atr_period, setStopLossAtrPeriod] = useState(14);
  const [stop_loss_atr_multiplier, setStopLossAtrMultiplier] = useState(2.0);
  const [stop_loss_support_lookback, setStopLossSupportLookback] = useState(20);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchExchanges = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) return;
      try {
        const connections = await getExchanges();
        setExchangeConnections(connections);
        if (connections.length > 0) {
          setSelectedExchange(connections[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch exchange connections", error);
        setError("Could not load your exchange connections.");
      }
    };
    fetchExchanges();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStrategy || !botName || !selectedExchange) {
      setError("Please fill all required fields.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await createBot({
        name: botName,
        strategy_name: selectedStrategy,
        strategy_params: (selectedStrategy === 'cassava_trend_following' || selectedStrategy === 'grid_trading') ? strategyParams : {},
        exchange_connection_id: selectedExchange,
        trade_type: tradeType,
        direction,
        leverage: tradeType === 'futures' ? leverage : 1,
        initial_balance: initialBalance,
        trading_pairs: selectedPairs.join(','),
        trade_interval_seconds,
        max_position_size_percent,
        max_trades_per_day,
        min_balance_threshold,
        max_daily_loss,
        stop_loss_type,
        stop_loss_percentage,
        stop_loss_timeframe,
        stop_loss_ema_period,
        stop_loss_atr_period,
        stop_loss_atr_multiplier,
        stop_loss_support_lookback
      });
      
      router.push('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create bot.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBacktest = async () => {
    if (!selectedExchange || selectedPairs.length === 0) {
      setError("Please select an exchange and at least one trading pair for backtesting.");
      return;
    }

    setBacktestLoading(true);
    setError(null);
    setLocalBacktestResult(null);
    setBacktestResult(null);

    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      setError('You must be logged in to run backtests.');
      setBacktestLoading(false);
      return;
    }

    // Get the strategy name from the selected strategy ID
    const selectedStrategyData = strategies.find(s => s.id === selectedStrategy);
    if (!selectedStrategyData) {
      setError('Invalid strategy selected.');
      setBacktestLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/v1/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          strategy_name: selectedStrategyData.name,
          strategy_params: strategyParams,
          symbol: strategyParams.symbol,
          exchange_connection_id: selectedExchange,
          timeframe: strategyParams.timeframe,
          start_date: '2023-01-01',
          end_date: '2024-01-01',
          initial_balance: 1000,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred.' }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result: BacktestResult = await response.json();
      setLocalBacktestResult(result);
      setBacktestResult(result);

    } catch (err: any) {
      setError(err.message || 'Failed to run backtest.');
    } finally {
      setBacktestLoading(false);
    }
  };

  const selectedStrategyData = useMemo(() => strategies.find(s => s.id === selectedStrategy), [selectedStrategy]);

  const renderStrategyOptions = () => {
    if (selectedStrategy === 'cassava_trend_following') {
      return (
        <Section icon={<PresentationChartLineIcon className="h-6 w-6 text-teal-400" />} title="Strategy Parameters">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <div>
              <label className="form-label">Timeframe</label>
              <select value={strategyParams.timeframe} onChange={e => setStrategyParams(p => ({ ...p, timeframe: e.target.value }))} className="w-full form-input">
                <option>4h</option>
                <option>6h</option>
                <option>12h</option>
                <option>1d</option>
              </select>
            </div>
            <div>
              <label className="form-label">Fast EMA</label>
              <input type="number" value={strategyParams.ema_fast} onChange={e => setStrategyParams(p => ({ ...p, ema_fast: parseInt(e.target.value) }))} className="w-full form-input" />
            </div>
            <div>
              <label className="form-label">Slow EMA (Buy)</label>
              <input type="number" value={strategyParams.ema_slow_buy} onChange={e => setStrategyParams(p => ({ ...p, ema_slow_buy: parseInt(e.target.value) }))} className="w-full form-input" />
            </div>
            <div>
              <label className="form-label">Slow EMA (Sell)</label>
              <input type="number" value={strategyParams.ema_slow_sell} onChange={e => setStrategyParams(p => ({ ...p, ema_slow_sell: parseInt(e.target.value) }))} className="w-full form-input" />
            </div>
            <div>
              <label className="form-label">DMI Length</label>
              <input type="number" value={strategyParams.dmi_length} onChange={e => setStrategyParams(p => ({ ...p, dmi_length: parseInt(e.target.value) }))} className="w-full form-input" />
            </div>
            <div>
              <label className="form-label">DI+ Buy Threshold</label>
              <input type="number" value={strategyParams.di_plus_buy_threshold} onChange={e => setStrategyParams(p => ({ ...p, di_plus_buy_threshold: parseInt(e.target.value) }))} className="w-full form-input" />
            </div>
            <div>
              <label className="form-label">DI+ Sell Threshold</label>
              <input type="number" value={strategyParams.di_plus_sell_threshold} onChange={e => setStrategyParams(p => ({ ...p, di_plus_sell_threshold: parseInt(e.target.value) }))} className="w-full form-input" />
            </div>
            <div>
              <label htmlFor="symbol" className="form-label">Cryptocurrency</label>
              <select id="symbol" name="symbol" value={strategyParams.symbol} onChange={e => setStrategyParams(p => ({ ...p, symbol: e.target.value }))} className="w-full form-input">
                <option value="BTCUSDT">BTCUSDT</option>
                <option value="ETHUSDT">ETHUSDT</option>
                <option value="BNBUSDT">BNBUSDT</option>
                <option value="SOLUSDT">SOLUSDT</option>
                <option value="SUIUSDT">SUIUSDT</option>
              </select>
            </div>
          </div>
          
          {/* Backtest Button */}
          <div className="mt-6">
            <button
              type="button"
              onClick={handleBacktest}
              disabled={backtestLoading || !selectedExchange || selectedPairs.length === 0}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {backtestLoading ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                  Running Backtest...
                </>
              ) : (
                <>
                  <BeakerIcon className="h-5 w-5 mr-2" />
                  Run Backtest
                </>
              )}
            </button>
          </div>

          {/* Backtest Results */}
          {backtestResult && (
            <div className="mt-6 bg-gray-700 p-4 rounded-lg">
              <h4 className="text-lg font-semibold mb-4">Backtest Results</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-400">Total Return</p>
                  <p className={`text-xl font-bold ${backtestResult.total_return >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {backtestResult.total_return.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Total Trades</p>
                  <p className="text-xl font-bold">{backtestResult.total_trades}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Win Rate</p>
                  <p className="text-xl font-bold">{backtestResult.win_rate.toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Max Drawdown</p>
                  <p className="text-xl font-bold text-red-500">{(backtestResult.max_drawdown * 100).toFixed(2)}%</p>
                </div>
              </div>
              {backtestResult.trades && backtestResult.trades.length > 0 && (
                <div className="mt-4 text-right">
                  <button
                    type="button"
                    onClick={() => router.push('/dashboard/backtest-details')}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
                  >
                    View Details
                  </button>
                </div>
              )}
            </div>
          )}
        </Section>
      );
    }

    if (selectedStrategy === 'grid_trading') {
      return (
        <Section icon={<PresentationChartLineIcon className="h-6 w-6 text-teal-400" />} title="Grid Trading Configuration">
          {/* Grid Type Selection */}
          <div className="mb-8">
            <h4 className="text-lg font-semibold mb-4 text-blue-400">Grid Algorithm</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { id: 'arithmetic', name: 'Arithmetic Grid', desc: 'Equal price intervals', icon: '📏' },
                { id: 'geometric', name: 'Geometric Grid', desc: 'Percentage-based spacing', icon: '📈' },
                { id: 'dynamic', name: 'Dynamic Grid', desc: 'Volatility-adaptive', icon: '⚡' },
                { id: 'fibonacci', name: 'Fibonacci Grid', desc: 'Fibonacci sequence levels', icon: '🌀' },
                { id: 'bollinger', name: 'Bollinger Band Grid', desc: 'BB-based levels', icon: '📊' },
                { id: 'support_resistance', name: 'Support/Resistance Grid', desc: 'S/R aligned', icon: '🎯' }
              ].map((gridType) => (
                <button
                  key={gridType.id}
                  type="button"
                  onClick={() => setStrategyParams(p => ({ ...p, grid_type: gridType.id }))}
                  className={`p-4 border rounded-lg text-left transition-all duration-200 ${
                    strategyParams.grid_type === gridType.id
                      ? 'border-blue-500 bg-blue-900/20 text-blue-300'
                      : 'border-gray-600 hover:border-gray-500 hover:bg-gray-800/50'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <span className="text-2xl">{gridType.icon}</span>
                    <div>
                      <h5 className="font-semibold text-sm mb-1">{gridType.name}</h5>
                      <p className="text-xs text-gray-400">{gridType.desc}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Grid Direction */}
          <div className="mb-8">
            <h4 className="text-lg font-semibold mb-4 text-green-400">Grid Direction</h4>
            <div className="grid grid-cols-3 gap-4">
              {[
                { id: 'long_only', name: 'Long Only', desc: 'Only buy orders (accumulate)', color: 'green' },
                { id: 'short_only', name: 'Short Only', desc: 'Only sell orders (profit)', color: 'red' },
                { id: 'neutral', name: 'Neutral', desc: 'Both buy and sell orders', color: 'blue' }
              ].map((direction) => (
                <button
                  key={direction.id}
                  type="button"
                  onClick={() => setStrategyParams(p => ({ ...p, grid_direction: direction.id }))}
                  className={`p-4 border rounded-lg text-center transition-all duration-200 ${
                    strategyParams.grid_direction === direction.id
                      ? `border-${direction.color}-500 bg-${direction.color}-900/20 text-${direction.color}-300`
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  <h5 className="font-semibold text-sm mb-1">{direction.name}</h5>
                  <p className="text-xs text-gray-400">{direction.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Basic Grid Parameters */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
            <div>
              <label className="form-label">Grid Levels</label>
              <input 
                type="number" 
                min="5" 
                max="50" 
                value={strategyParams.grid_levels || 10} 
                onChange={e => setStrategyParams(p => ({ ...p, grid_levels: parseInt(e.target.value) }))} 
                className="w-full form-input" 
              />
              <p className="text-xs text-gray-400 mt-1">Number of price levels (5-50)</p>
            </div>
            <div>
              <label className="form-label">Grid Spacing (%)</label>
              <input 
                type="number" 
                step="0.1" 
                min="0.1" 
                max="10" 
                value={strategyParams.grid_spacing_percent || 1.0} 
                onChange={e => setStrategyParams(p => ({ ...p, grid_spacing_percent: parseFloat(e.target.value) }))} 
                className="w-full form-input" 
              />
              <p className="text-xs text-gray-400 mt-1">% between levels</p>
            </div>
            <div>
              <label className="form-label">Investment per Grid ($)</label>
              <input 
                type="number" 
                min="10" 
                value={strategyParams.investment_per_grid || 100} 
                onChange={e => setStrategyParams(p => ({ ...p, investment_per_grid: parseFloat(e.target.value) }))} 
                className="w-full form-input" 
              />
              <p className="text-xs text-gray-400 mt-1">USDT per grid level</p>
            </div>
            <div>
              <label className="form-label">Max Total Investment ($)</label>
              <input 
                type="number" 
                min="100" 
                value={strategyParams.max_total_investment || 1000} 
                onChange={e => setStrategyParams(p => ({ ...p, max_total_investment: parseFloat(e.target.value) }))} 
                className="w-full form-input" 
              />
              <p className="text-xs text-gray-400 mt-1">Maximum total USDT</p>
            </div>
          </div>

          {/* Algorithm-Specific Parameters */}
          {strategyParams.grid_type === 'dynamic' && (
            <div className="bg-gray-800 p-4 rounded-lg mb-6">
              <h5 className="text-md font-semibold mb-3 text-yellow-400">⚡ Dynamic Grid Settings</h5>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <label className="form-label">Volatility Lookback (days)</label>
                  <input 
                    type="number" 
                    min="5" 
                    max="100" 
                    value={strategyParams.volatility_lookback || 20} 
                    onChange={e => setStrategyParams(p => ({ ...p, volatility_lookback: parseInt(e.target.value) }))} 
                    className="w-full form-input" 
                  />
                </div>
                <div>
                  <label className="form-label">Volatility Multiplier</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    min="0.5" 
                    max="5" 
                    value={strategyParams.volatility_multiplier || 2.0} 
                    onChange={e => setStrategyParams(p => ({ ...p, volatility_multiplier: parseFloat(e.target.value) }))} 
                    className="w-full form-input" 
                  />
                </div>
                <div>
                  <label className="form-label">Rebalance Threshold (%)</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    min="0.01" 
                    max="1" 
                    value={strategyParams.rebalance_threshold || 0.1} 
                    onChange={e => setStrategyParams(p => ({ ...p, rebalance_threshold: parseFloat(e.target.value) }))} 
                    className="w-full form-input" 
                  />
                </div>
              </div>
            </div>
          )}

          {strategyParams.grid_type === 'fibonacci' && (
            <div className="bg-gray-800 p-4 rounded-lg mb-6">
              <h5 className="text-md font-semibold mb-3 text-purple-400">🌀 Fibonacci Grid Settings</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Base Spacing (%)</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    min="0.1" 
                    max="2" 
                    value={strategyParams.fibonacci_base_spacing || 0.5} 
                    onChange={e => setStrategyParams(p => ({ ...p, fibonacci_base_spacing: parseFloat(e.target.value) }))} 
                    className="w-full form-input" 
                  />
                  <p className="text-xs text-gray-400 mt-1">Base percentage for Fibonacci scaling</p>
                </div>
              </div>
            </div>
          )}

          {strategyParams.grid_type === 'bollinger' && (
            <div className="bg-gray-800 p-4 rounded-lg mb-6">
              <h5 className="text-md font-semibold mb-3 text-indigo-400">📊 Bollinger Band Grid Settings</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="form-label">BB Period</label>
                  <input 
                    type="number" 
                    min="10" 
                    max="50" 
                    value={strategyParams.bollinger_period || 20} 
                    onChange={e => setStrategyParams(p => ({ ...p, bollinger_period: parseInt(e.target.value) }))} 
                    className="w-full form-input" 
                  />
                </div>
                <div>
                  <label className="form-label">Standard Deviation</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    min="1" 
                    max="3" 
                    value={strategyParams.bollinger_std_dev || 2.0} 
                    onChange={e => setStrategyParams(p => ({ ...p, bollinger_std_dev: parseFloat(e.target.value) }))} 
                    className="w-full form-input" 
                  />
                </div>
              </div>
            </div>
          )}

          {/* Risk Management for Grid Trading */}
          <div className="bg-red-900/20 border border-red-700 p-4 rounded-lg">
            <h5 className="text-md font-semibold mb-3 text-red-400">🛡️ Grid Risk Management</h5>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="form-label">Stop Loss (%)</label>
                <input 
                  type="number" 
                  step="0.5" 
                  min="5" 
                  max="50" 
                  value={strategyParams.stop_loss_percent || 15} 
                  onChange={e => setStrategyParams(p => ({ ...p, stop_loss_percent: parseFloat(e.target.value) }))} 
                  className="w-full form-input" 
                />
                <p className="text-xs text-gray-400 mt-1">Stop entire grid</p>
              </div>
              <div>
                <label className="form-label">Take Profit (%)</label>
                <input 
                  type="number" 
                  step="0.5" 
                  min="10" 
                  max="100" 
                  value={strategyParams.take_profit_percent || 25} 
                  onChange={e => setStrategyParams(p => ({ ...p, take_profit_percent: parseFloat(e.target.value) }))} 
                  className="w-full form-input" 
                />
                <p className="text-xs text-gray-400 mt-1">Take profit entire grid</p>
              </div>
              <div>
                <label className="form-label">Max Open Orders</label>
                <input 
                  type="number" 
                  min="5" 
                  max="100" 
                  value={strategyParams.max_open_orders || 20} 
                  onChange={e => setStrategyParams(p => ({ ...p, max_open_orders: parseInt(e.target.value) }))} 
                  className="w-full form-input" 
                />
                <p className="text-xs text-gray-400 mt-1">Limit concurrent orders</p>
              </div>
            </div>
          </div>
        </Section>
      );
    }

    return null;
  };

  const renderStopLossOptions = () => {
    switch (stop_loss_type) {
      case 'fixed_percentage':
      case 'trailing_max_price':
        return (
          <div className="space-y-4">
            <div>
              <label htmlFor="sl-percentage" className="block text-sm font-medium mb-1">Percentage</label>
              <input type="number" id="sl-percentage" value={stop_loss_percentage} onChange={e => setStopLossPercentage(parseFloat(e.target.value))} className="w-full form-input" />
            </div>
            {stop_loss_type === 'trailing_max_price' && (
              <div>
                <label htmlFor="sl-timeframe" className="block text-sm font-medium mb-1">Timeframe</label>
                <select id="sl-timeframe" value={stop_loss_timeframe} onChange={e => setStopLossTimeframe(e.target.value)} className="w-full form-input">
                  <option>1h</option>
                  <option>4h</option>
                  <option>1d</option>
                </select>
              </div>
            )}
          </div>
        );
      case 'ema_based':
        return (
            <div className="space-y-4">
                <div>
                    <label htmlFor="sl-ema-period" className="block text-sm font-medium mb-1">EMA Period</label>
                    <input type="number" id="sl-ema-period" value={stop_loss_ema_period} onChange={e => setStopLossEmaPeriod(parseInt(e.target.value))} className="w-full form-input" />
                </div>
                <div>
                    <label htmlFor="sl-ema-percentage" className="block text-sm font-medium mb-1">Offset Percentage</label>
                    <input type="number" id="sl-ema-percentage" value={stop_loss_percentage} onChange={e => setStopLossPercentage(parseFloat(e.target.value))} className="w-full form-input" />
                </div>
            </div>
        );
      case 'atr_based':
        return (
            <div className="space-y-4">
                <div>
                    <label htmlFor="sl-atr-period" className="block text-sm font-medium mb-1">ATR Period</label>
                    <input type="number" id="sl-atr-period" value={stop_loss_atr_period} onChange={e => setStopLossAtrPeriod(parseInt(e.target.value))} className="w-full form-input" />
                </div>
                <div>
                    <label htmlFor="sl-atr-multiplier" className="block text-sm font-medium mb-1">ATR Multiplier</label>
                    <input type="number" step="0.1" id="sl-atr-multiplier" value={stop_loss_atr_multiplier} onChange={e => setStopLossAtrMultiplier(parseFloat(e.target.value))} className="w-full form-input" />
                </div>
            </div>
        );
      case 'support_level':
        return (
            <div>
                <label htmlFor="sl-support-lookback" className="block text-sm font-medium mb-1">Support Lookback Period</label>
                <input type="number" id="sl-support-lookback" value={stop_loss_support_lookback} onChange={e => setStopLossSupportLookback(parseInt(e.target.value))} className="w-full form-input" />
            </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white pb-12">
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center py-4">
            <button onClick={() => router.back()} className="mr-4 p-2 hover:bg-gray-700 rounded-lg">
              <ArrowLeftIcon className="h-6 w-6" />
            </button>
            <div className="flex items-center">
              <CogIcon className="h-8 w-8 text-blue-500 mr-3" />
              <h1 className="text-2xl font-bold">Create New Trading Bot</h1>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          {error && (
            <div className="bg-red-900 text-red-200 p-3 rounded mb-4 border border-red-700">
              {error}
            </div>
          )}
          
          {/* Section 1: Bot Identity */}
          <Section icon={<BeakerIcon className="h-6 w-6 text-purple-400" />} title="Bot Identity">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label htmlFor="botName" className="form-label">Bot Name</label>
                    <input type="text" id="botName" value={botName} onChange={(e) => setBotName(e.target.value)} className="w-full form-input" placeholder="e.g., My ETH Trend Follower" required />
                </div>
                <div>
                    <label htmlFor="exchange" className="form-label">Exchange Connection</label>
                    <select id="exchange" value={selectedExchange ?? ''} onChange={(e) => setSelectedExchange(parseInt(e.target.value))} className="w-full form-input" required disabled={exchangeConnections.length === 0}>
                    {exchangeConnections.length === 0 ? <option>No connections found</option> : exchangeConnections.map((conn) => (
                        <option key={conn.id} value={conn.id}>{conn.exchange_name} ({conn.api_key?.substring(0, 4)}...)</option>
                    ))}
                    </select>
                </div>
            </div>
          </Section>

          {/* Section 2: Strategy */}
          <Section icon={<PresentationChartLineIcon className="h-6 w-6 text-teal-400" />} title="Trading Strategy">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {strategies.map((strategy) => (
                <div key={strategy.id} className={`strategy-card ${selectedStrategy === strategy.id ? 'strategy-card-selected' : ''}`} onClick={() => setSelectedStrategy(strategy.id)}>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold">{strategy.name}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${strategy.risk === 'low' ? 'bg-green-900 text-green-300' : strategy.risk === 'medium' ? 'bg-yellow-900 text-yellow-300' : 'bg-red-900 text-red-300'}`}>
                      {strategy.risk} risk
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mb-2">{strategy.description}</p>
                  <p className="text-xs text-gray-500">Min balance: ${strategy.minBalance.toLocaleString()}</p>
                </div>
              ))}
            </div>
            
            {/* Cassava Strategy Notification */}
            {selectedStrategy === 'cassava_trend_following' && (
              <div className="mt-6 bg-blue-900/30 border border-blue-600 rounded-lg p-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-blue-300">
                      Internal Stoploss System
                    </h3>
                    <div className="mt-2 text-sm text-blue-200">
                      <p>
                        The <strong>Cassava Trend Following Strategy</strong> uses its own tested and optimized internal stoploss logic:
                      </p>
                      <ul className="mt-2 list-disc list-inside space-y-1">
                        <li><strong>Long positions:</strong> EMA25 trailing stoploss</li>
                        <li><strong>Short positions:</strong> Fractal-based stoploss with dynamic adjustments</li>
                        <li><strong>Exit conditions:</strong> EMA8 for shorts, EMA25 for longs</li>
                      </ul>
                      <p className="mt-2 text-blue-100">
                        <strong>Note:</strong> Any stoploss settings configured below will be <strong>ignored</strong> when using this strategy.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Section>

          {renderStrategyOptions()}

          {/* Section 3: Trading Configuration */}
          <Section icon={<GlobeAltIcon className="h-6 w-6 text-indigo-400" />} title="Trading Configuration">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Trading Pairs */}
              <div>
                <label className="form-label">Trading Pairs</label>
                <TradingPairsSelect
                  selectedPairs={selectedPairs}
                  onPairsChange={(pairs) => setSelectedPairs(pairs)}
                />
              </div>

              {/* Trade Type & Direction */}
              <div className="space-y-6">
                <div>
                  <label className="form-label">Trade Type</label>
                  <div className="flex gap-4 mt-2">
                    <button type="button" onClick={() => setTradeType('spot')} className={`trade-type-btn ${tradeType === 'spot' ? 'trade-type-btn-selected' : ''}`}>Spot</button>
                    <button type="button" onClick={() => setTradeType('futures')} className={`trade-type-btn ${tradeType === 'futures' ? 'trade-type-btn-selected' : ''}`}>Futures</button>
                  </div>
                </div>

                {tradeType === 'futures' && (
                  <div>
                    <label className="form-label">Direction</label>
                    <div className="flex gap-4 mt-2">
                      <button type="button" onClick={() => setDirection('long')} className={`trade-type-btn ${direction === 'long' ? 'trade-type-btn-selected' : ''}`}>Long</button>
                      <button type="button" onClick={() => setDirection('short')} className={`trade-type-btn ${direction === 'short' ? 'trade-type-btn-selected' : ''}`}>Short</button>
                      <button type="button" onClick={() => setDirection('both')} className={`trade-type-btn ${direction === 'both' ? 'trade-type-btn-selected' : ''}`}>Both</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
             {tradeType === 'futures' && (
                <div className="mt-6">
                  <label htmlFor="leverage" className="form-label">Leverage</label>
                  <input type="range" id="leverage" min="1" max="100" value={leverage} onChange={(e) => setLeverage(parseInt(e.target.value))} className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer mt-2" />
                  <div className="text-center mt-1">{leverage}x</div>
                </div>
              )}
          </Section>

          {/* Section 4: Risk Management */}
          <Section icon={<ShieldCheckIcon className="h-6 w-6 text-green-400" />} title="Risk Management">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label htmlFor="initial-balance" className="form-label">Initial Balance (USD)</label>
                <input type="number" id="initial-balance" value={initialBalance} onChange={e => setInitialBalance(parseFloat(e.target.value))} className="w-full form-input" />
              </div>
              <div>
                <label htmlFor="max-pos-size" className="form-label">Max Position Size (% of Balance)</label>
                <input type="number" id="max-pos-size" value={max_position_size_percent} onChange={e => setMaxPositionSizePercent(parseFloat(e.target.value))} className="w-full form-input" />
              </div>
              <div>
                <label htmlFor="trade-interval" className="form-label">Trade Interval (seconds)</label>
                <input type="number" id="trade-interval" value={trade_interval_seconds} onChange={e => setTradeIntervalSeconds(parseInt(e.target.value))} className="w-full form-input" />
              </div>
              <div>
                <label htmlFor="max-trades-day" className="form-label">Max Trades Per Day</label>
                <input type="number" id="max-trades-day" value={max_trades_per_day ?? ''} onChange={e => setMaxTradesPerDay(e.target.value ? parseInt(e.target.value) : null)} placeholder="Optional" className="w-full form-input" />
              </div>
              <div>
                <label htmlFor="min-balance" className="form-label">Min Balance Threshold (USD)</label>
                <input type="number" id="min-balance" value={min_balance_threshold ?? ''} onChange={e => setMinBalanceThreshold(e.target.value ? parseFloat(e.target.value) : null)} placeholder="Optional" className="w-full form-input" />
              </div>
              <div>
                <label htmlFor="max-daily-loss" className="form-label">Max Daily Loss (USD)</label>
                <input type="number" id="max-daily-loss" value={max_daily_loss ?? ''} onChange={e => setMaxDailyLoss(e.target.value ? parseFloat(e.target.value) : null)} placeholder="Optional" className="w-full form-input" />
              </div>
            </div>
            
            <div className="mt-8">
                <h3 className="text-lg font-semibold mb-4 text-gray-300">Advanced Stop Loss</h3>
                
                {/* Cassava Strategy Stoploss Disabled Notice */}
                {selectedStrategy === 'cassava_trend_following' && (
                  <div className="mb-4 bg-yellow-900/30 border border-yellow-600 rounded-lg p-3">
                    <div className="flex items-center">
                      <svg className="h-5 w-5 text-yellow-400 mr-2" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm text-yellow-200">
                        <strong>Stoploss settings disabled:</strong> The Cassava strategy uses its own internal stoploss system.
                      </span>
                    </div>
                  </div>
                )}
                
                <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 ${selectedStrategy === 'cassava_trend_following' ? 'opacity-50 pointer-events-none' : ''}`}>
                    <div>
                        <label htmlFor="stop-loss-type" className="form-label">Stop Loss Type</label>
                        <select id="stop-loss-type" value={stop_loss_type} onChange={e => setStopLossType(e.target.value)} className="w-full form-input">
                            {stopLossTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                    </div>
                    <div className="bg-gray-800 p-4 rounded-md border border-gray-700">
                        {renderStopLossOptions()}
                    </div>
                </div>
            </div>
          </Section>

          {/* Summary & Submit */}
          <div className="sticky bottom-0 bg-gray-900/80 backdrop-blur-sm py-4">
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
                <BotSummary data={{ botName, selectedStrategyData, tradeType, leverage, initialBalance, stop_loss_percentage, selectedPairs }}/>
                <button type="submit" disabled={isLoading} className="w-full mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white font-bold py-3 px-4 rounded-lg transition-colors">
                {isLoading ? 'Creating Bot...' : 'Launch Bot'}
                </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

const Section: React.FC<{ icon: React.ReactNode, title: string, children: React.ReactNode }> = ({ icon, title, children }) => (
  <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
    <div className="flex items-center mb-4">
      {icon}
      <h2 className="text-xl font-bold ml-3">{title}</h2>
    </div>
    {children}
  </div>
);

const BotSummary: React.FC<{ data: any }> = ({ data }) => (
    <div className="text-sm">
        <h3 className="font-bold text-lg mb-2">Bot Summary</h3>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <p><span className="font-semibold text-gray-400">Name:</span> {data.botName || 'Not set'}</p>
            <p><span className="font-semibold text-gray-400">Strategy:</span> {data.selectedStrategyData?.name || 'Not set'}</p>
            <p><span className="font-semibold text-gray-400">Trade Type:</span> {data.tradeType}</p>
            {data.tradeType === 'futures' && <p><span className="font-semibold text-gray-400">Leverage:</span> {data.leverage}x</p>}
            <p><span className="font-semibold text-gray-400">Initial Balance:</span> ${data.initialBalance.toLocaleString()}</p>
            <p><span className="font-semibold text-gray-400">Stop Loss:</span> 
              {data.selectedStrategyData?.id === 'cassava_trend_following' ? (
                <span className="text-blue-400">Internal (EMA25/Fractal)</span>
              ) : (
                `${data.stop_loss_percentage}%`
              )}
            </p>
            <p><span className="font-semibold text-gray-400">Trading Pairs:</span> {data.selectedPairs.length} selected</p>
        </div>
    </div>
);

// Add some base styles to globals.css if they don't exist
/*
.form-label {
  @apply block text-sm font-medium mb-2 text-gray-300;
}
.form-input {
  @apply w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500;
}
.strategy-card {
  @apply p-4 border rounded-lg cursor-pointer transition-colors border-gray-600 hover:border-gray-500;
}
.strategy-card-selected {
  @apply border-blue-500 bg-blue-900/20;
}
.pair-toggle {
  @apply w-full px-3 py-2 text-sm text-center rounded-md transition-colors bg-gray-700 hover:bg-gray-600;
}
.pair-toggle-selected {
  @apply bg-blue-600 text-white hover:bg-blue-500;
}
.trade-type-btn {
    @apply px-4 py-2 rounded-md font-semibold transition-colors bg-gray-700 hover:bg-gray-600;
}
.trade-type-btn-selected {
    @apply bg-blue-600 text-white hover:bg-blue-500;
}
*/ 