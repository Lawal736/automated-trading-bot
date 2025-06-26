"use client";

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getBotById, updateBot, CreateBotPayload } from '../../../../lib/bots';
import { getExchangeConnections, ExchangeConnection } from '../../../../lib/exchanges';
import TradingPairsSelect from '../../../../components/TradingPairsSelect';

// Re-using the same UI components and icons
import { 
  CurrencyDollarIcon,
  CogIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';


export default function EditBotPage() {
  const router = useRouter();
  const params = useParams();
  const botId = Number(params.botId);

  const [formData, setFormData] = useState<Partial<CreateBotPayload>>({});
  const [exchangeConnections, setExchangeConnections] = useState<ExchangeConnection[]>([]);
  const [selectedPairs, setSelectedPairs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState('basic');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !botId) {
      router.push('/login');
      return;
    }

    async function fetchData(token: string) {
      try {
        setLoading(true);
        const [botData, connectionsData] = await Promise.all([
          getBotById(botId),
          getExchangeConnections()
        ]);
        
        // The API returns trading_pairs as a string, but the form expects a string.
        // The getBotById function already transforms it to an array, so we join it back.
        const botPayload = {
            ...botData,
            trading_pairs: Array.isArray(botData.trading_pairs) ? botData.trading_pairs.join(', ') : botData.trading_pairs,
        };

        setFormData(botPayload);
        // Set selected pairs for the TradingPairsSelect component
        if (Array.isArray(botData.trading_pairs)) {
            setSelectedPairs(botData.trading_pairs);
        } else if (typeof botData.trading_pairs === 'string') {
            setSelectedPairs(botData.trading_pairs.split(',').map(p => p.trim()).filter(p => p));
        }
        setExchangeConnections(connectionsData);
        setError(null);
      } catch (err) {
        setError('Failed to load bot or exchange connection data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData(token);
  }, [botId, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    
    let processedValue: string | number | undefined = value;
    if (type === 'number') {
      processedValue = value === '' ? undefined : Number(value);
    }
  
    setFormData(prev => ({ ...prev, [name]: processedValue }));
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError("Authentication failed. Please log in again.");
      return;
    }
    
    if (!formData.exchange_connection_id) {
        setError("Exchange Connection is required.");
        return;
    }

    // Ensure numeric fields are numbers
    const payload: Partial<CreateBotPayload> = {
        ...formData,
        leverage: Number(formData.leverage || 1),
        initial_balance: Number(formData.initial_balance || 0),
        trade_interval_seconds: Number(formData.trade_interval_seconds || 60),
        max_position_size_percent: Number(formData.max_position_size_percent || 10),
        stop_loss_percentage: Number(formData.stop_loss_percentage),
        stop_loss_ema_period: Number(formData.stop_loss_ema_period),
        stop_loss_atr_period: Number(formData.stop_loss_atr_period),
        stop_loss_atr_multiplier: Number(formData.stop_loss_atr_multiplier),
        stop_loss_support_lookback: Number(formData.stop_loss_support_lookback),
    };
    
    try {
      await updateBot(botId, payload);
      setSuccess('Bot updated successfully!');
      setTimeout(() => router.push('/dashboard'), 2000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update bot.');
      console.error(err);
    }
  };

  if (loading) {
    return <div className="text-center py-10">Loading bot data...</div>;
  }

  // Render Section function
  const renderSection = (title: string, sectionId: string, children: React.ReactNode) => (
    <div className={`mb-4 ${activeSection === sectionId ? '' : 'opacity-50'}`}>
      <h3 
        className="text-lg font-semibold text-white mb-2 cursor-pointer"
        onClick={() => setActiveSection(sectionId)}
      >
        {title}
      </h3>
      {activeSection === sectionId && <div className="bg-gray-800 p-4 rounded-lg">{children}</div>}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8 text-white">
      <h1 className="text-2xl font-bold mb-6">Edit Bot: {formData.name || ''}</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information Section */}
        {renderSection('Basic Information', 'basic', (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <label htmlFor="name" className="block text-sm font-medium">Bot Name</label>
                <input type="text" name="name" id="name" value={formData.name || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500" />
            </div>
            <div>
              <label htmlFor="strategy_name" className="block text-sm font-medium">Strategy</label>
              <input type="text" name="strategy_name" id="strategy_name" value={formData.strategy_name || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" readOnly/>
            </div>
            <div className="md:col-span-2">
                <label htmlFor="description" className="block text-sm font-medium">Description</label>
                <textarea name="description" id="description" value={formData.description || ''} onChange={handleChange} rows={3} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm"></textarea>
            </div>
          </div>
        ))}
        
        {/* Trading Configuration Section */}
        {renderSection('Trading Configuration', 'trading', (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="exchange_connection_id" className="block text-sm font-medium">Exchange Connection</label>
                <select name="exchange_connection_id" id="exchange_connection_id" value={formData.exchange_connection_id || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm">
                    <option value="">Select Connection</option>
                    {exchangeConnections.map(c => (
                        <option key={c.id} value={c.id}>{c.exchange_name} ({c.api_key.substring(0, 4)}...)</option>
                    ))}
                </select>
              </div>
              <div>
                  <label htmlFor="trading_pairs" className="block text-sm font-medium">Trading Pairs</label>
                  <TradingPairsSelect
                    selectedPairs={selectedPairs}
                    onPairsChange={(pairs) => {
                      setSelectedPairs(pairs);
                      setFormData(prev => ({ ...prev, trading_pairs: pairs.join(', ') }));
                    }}
                  />
              </div>
              <div>
                  <label htmlFor="trade_type" className="block text-sm font-medium">Trade Type</label>
                  <select name="trade_type" id="trade_type" value={formData.trade_type || 'spot'} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm">
                      <option value="spot">Spot</option>
                      <option value="futures">Futures</option>
                  </select>
              </div>
              <div>
                  <label htmlFor="direction" className="block text-sm font-medium">Direction</label>
                  <select name="direction" id="direction" value={formData.direction || 'long'} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm">
                      <option value="long">Long</option>
                      <option value="short">Short</option>
                      <option value="both">Both</option>
                  </select>
              </div>
              <div>
                  <label htmlFor="leverage" className="block text-sm font-medium">Leverage</label>
                  <input type="number" name="leverage" id="leverage" value={formData.leverage || 1} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
              </div>
              <div>
                  <label htmlFor="initial_balance" className="block text-sm font-medium">Initial Balance (USD)</label>
                  <input type="number" step="0.01" name="initial_balance" id="initial_balance" value={formData.initial_balance || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
              </div>
          </div>
        ))}
        
        {/* Risk Management Section */}
        {renderSection('Risk Management', 'risk', (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="max_position_size_percent" className="block text-sm font-medium">Max Position Size (%)</label>
              <input type="number" step="0.1" name="max_position_size_percent" value={formData.max_position_size_percent || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
            </div>
            <div>
              <label htmlFor="max_trades_per_day" className="block text-sm font-medium">Max Trades Per Day</label>
              <input type="number" name="max_trades_per_day" value={formData.max_trades_per_day || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
            </div>
            <div>
              <label htmlFor="min_balance_threshold" className="block text-sm font-medium">Min Balance Threshold (USD)</label>
              <input type="number" step="0.01" name="min_balance_threshold" value={formData.min_balance_threshold || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
            </div>
            <div>
              <label htmlFor="max_daily_loss" className="block text-sm font-medium">Max Daily Loss (USD)</label>
              <input type="number" step="0.01" name="max_daily_loss" value={formData.max_daily_loss || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
            </div>
            <div>
              <label htmlFor="trade_interval_seconds" className="block text-sm font-medium">Trade Interval (seconds)</label>
              <input type="number" name="trade_interval_seconds" value={formData.trade_interval_seconds || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
            </div>
          </div>
        ))}

        {/* Advanced Stop-Loss Section */}
        {renderSection('Advanced Stop-Loss', 'stoploss', (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="stop_loss_type" className="block text-sm font-medium">Stop-Loss Type</label>
              <select name="stop_loss_type" id="stop_loss_type" value={formData.stop_loss_type || 'fixed_percentage'} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm">
                <option value="fixed_percentage">Fixed Percentage</option>
                <option value="trailing_max_price">Trailing Max Price</option>
                <option value="ema_based">EMA Based</option>
                <option value="atr_based">ATR Based</option>
                <option value="support_level">Support Level</option>
              </select>
            </div>

            {formData.stop_loss_type === 'fixed_percentage' && (
              <div>
                <label htmlFor="stop_loss_percentage" className="block text-sm font-medium">Stop-Loss Percentage (%)</label>
                <input type="number" step="0.1" name="stop_loss_percentage" value={formData.stop_loss_percentage || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
              </div>
            )}
            
            {['trailing_max_price', 'ema_based', 'atr_based', 'support_level'].includes(formData.stop_loss_type!) && (
              <div>
                <label htmlFor="stop_loss_timeframe" className="block text-sm font-medium">Timeframe</label>
                <select name="stop_loss_timeframe" value={formData.stop_loss_timeframe || '4h'} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm">
                    <option value="1m">1 Minute</option>
                    <option value="5m">5 Minutes</option>
                    <option value="15m">15 Minutes</option>
                    <option value="1h">1 Hour</option>
                    <option value="4h">4 Hours</option>
                    <option value="1d">1 Day</option>
                </select>
              </div>
            )}

            {formData.stop_loss_type === 'ema_based' && (
              <div>
                <label htmlFor="stop_loss_ema_period" className="block text-sm font-medium">EMA Period</label>
                <input type="number" name="stop_loss_ema_period" value={formData.stop_loss_ema_period || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
              </div>
            )}

            {formData.stop_loss_type === 'atr_based' && (
              <>
                <div>
                  <label htmlFor="stop_loss_atr_period" className="block text-sm font-medium">ATR Period</label>
                  <input type="number" name="stop_loss_atr_period" value={formData.stop_loss_atr_period || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
                </div>
                <div>
                  <label htmlFor="stop_loss_atr_multiplier" className="block text-sm font-medium">ATR Multiplier</label>
                  <input type="number" step="0.1" name="stop_loss_atr_multiplier" value={formData.stop_loss_atr_multiplier || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
                </div>
              </>
            )}

            {formData.stop_loss_type === 'support_level' && (
              <div>
                <label htmlFor="stop_loss_support_lookback" className="block text-sm font-medium">Support Lookback Period</label>
                <input type="number" name="stop_loss_support_lookback" value={formData.stop_loss_support_lookback || ''} onChange={handleChange} className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm" />
              </div>
            )}
          </div>
        ))}

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-4 pt-4">
          {error && <p className="text-sm text-red-500">{error}</p>}
          {success && <p className="text-sm text-green-500">{success}</p>}
          <button type="button" onClick={() => router.back()} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">
            Cancel
          </button>
          <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded">
            Save Changes
          </button>
        </div>
      </form>
    </div>
  );
}

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