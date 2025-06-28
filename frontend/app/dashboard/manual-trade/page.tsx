"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeftIcon, 
  BoltIcon
} from '@heroicons/react/24/outline';
import { logActivity, ActivityCreate } from '../../../lib/activities';
import { getTickerPrice, executeTrade, TradeOrder, getTopTradingPairs } from '../../../lib/exchanges';
import { toast } from "sonner";

interface TradeForm {
  pair: string;
  side: 'buy' | 'sell';
  orderType: 'market' | 'limit';
  tradeType: 'spot' | 'futures';
  leverage: number;
  amount: number;
  price?: number;
  stopLoss?: number;
  total: number;
}

export default function ManualTradePage() {
  const router = useRouter();
  const [availablePairs, setAvailablePairs] = useState<string[]>(['BTC/USDT']);
  const [tradeForm, setTradeForm] = useState<TradeForm>({
    pair: 'BTC/USDT',
    side: 'buy',
    orderType: 'market',
    tradeType: 'spot',
    leverage: 1,
    amount: 0,
    price: undefined,
    stopLoss: undefined,
    total: 0
  });
  const [isLoading, setIsLoading] = useState(false);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [isLoadingPrice, setIsLoadingPrice] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPairs = async () => {
      try {
        const pairs = await getTopTradingPairs();
        setAvailablePairs(pairs);
        if (pairs.length > 0 && !pairs.includes(tradeForm.pair)) {
          setTradeForm(prev => ({ ...prev, pair: pairs[0] }));
        }
      } catch (error) {
        console.error('Failed to fetch trading pairs:', error);
        // Keep default pairs
      }
    };
    fetchPairs();
  }, []);

  useEffect(() => {
    const fetchPrice = async () => {
      setIsLoadingPrice(true);
      try {
        const urlSymbol = tradeForm.pair.replace('/', '-');
        const ticker = await getTickerPrice(urlSymbol, 'binance');
        if (ticker && ticker.last_price) {
          const price = Number(ticker.last_price);
          setCurrentPrice(price);
          if (tradeForm.orderType === 'market') {
            setTradeForm(prev => ({ ...prev, price }));
          }
        } else {
          setCurrentPrice(null);
          toast.error(`Could not fetch price for ${tradeForm.pair}`);
        }
      } catch (error) {
        setCurrentPrice(null);
        toast.error("Failed to fetch price");
      } finally {
        setIsLoadingPrice(false);
      }
    };
    fetchPrice();
  }, [tradeForm.pair]);
  

  const handleAmountChange = (amount: number) => {
    const price = tradeForm.orderType === 'market' ? currentPrice : tradeForm.price;
    setTradeForm(prev => ({
      ...prev,
      amount,
      total: amount * (price || 0)
    }));
  };

  const handlePriceChange = (price: number) => {
    setTradeForm(prev => ({
      ...prev,
      price,
      total: (prev.amount || 0) * price
    }));
  };

  const handlePairChange = (pair: string) => {
    setTradeForm(prev => ({
      ...prev,
      pair,
    }));
  };
  
  const handleTradeTypeChange = (type: 'spot' | 'futures') => {
    setTradeForm(prev => ({
      ...prev,
      tradeType: type,
      leverage: type === 'spot' ? 1 : prev.leverage,
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (tradeForm.amount <= 0) {
      toast.error("Amount must be greater than zero.");
      return;
    }
    setIsLoading(true);
    setError(null);

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('Authentication token not found.');
      setIsLoading(false);
      return;
    }

    const order: TradeOrder = {
      symbol: tradeForm.pair,
      side: tradeForm.side,
      order_type: tradeForm.orderType,
      trade_type: tradeForm.tradeType,
      amount: tradeForm.amount,
      price: tradeForm.orderType === 'limit' ? tradeForm.price : undefined,
      stop_loss: tradeForm.stopLoss !== undefined && !isNaN(tradeForm.stopLoss) ? tradeForm.stopLoss : undefined,
    };

    try {
      // For now, we'll assume the exchange is 'binance'
      console.log("Attempting to execute trade...");
      const tradeResult = await executeTrade('binance', order);
      console.log("Trade execution successful:", tradeResult);
      toast.success(`Trade executed successfully! Order ID: ${tradeResult.id}`);

      // Also log the activity
      console.log("Attempting to log activity...");
      const activityLog: ActivityCreate = {
        type: "MANUAL_TRADE",
        description: `Manual ${tradeForm.tradeType} ${tradeForm.side} order for ${tradeForm.amount} ${tradeForm.pair.split('/')[0]} at ${tradeForm.orderType} price. Status: ${tradeResult.status}`,
        amount: tradeForm.total
      };
      await logActivity(activityLog);
      console.log("Activity logged successfully.");

      router.push('/dashboard/reports');
    } catch (error: any) {
      toast.error(`Trade failed: ${error.message}`);
      console.error("Trade execution error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const isMarketOrder = tradeForm.orderType === 'market';

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <main className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="mb-8">
          <button onClick={() => router.back()} className="flex items-center text-gray-400 hover:text-white mb-4">
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back
          </button>
          <h1 className="text-3xl font-bold flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 mr-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
            </svg>
            Manual Trade
          </h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Trading Pair */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h2 className="text-xl font-bold mb-4">Trading Pair</h2>
              <select
                value={tradeForm.pair}
                onChange={(e) => handlePairChange(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 focus:ring-2 focus:ring-green-500"
              >
                {availablePairs.map((pair) => (
                  <option key={pair} value={pair}>
                    {pair}
                  </option>
                ))}
              </select>
              <div className="mt-4 p-3 bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-400">Current Price</p>
                <p className="text-2xl font-bold">
                  {isLoadingPrice ? 'Loading...' : currentPrice ? `$${currentPrice.toLocaleString()}` : 'N/A'}
                </p>
              </div>
            </div>

            {/* Trade Type */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h2 className="text-xl font-bold mb-4">Trade Type</h2>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => handleTradeTypeChange('spot')}
                  className={`p-4 border rounded-lg font-semibold transition-colors ${
                    tradeForm.tradeType === 'spot'
                      ? 'border-blue-500 bg-blue-900/20 text-blue-300'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  Spot
                </button>
                <button
                  type="button"
                  onClick={() => handleTradeTypeChange('futures')}
                  className={`p-4 border rounded-lg font-semibold transition-colors ${
                    tradeForm.tradeType === 'futures'
                      ? 'border-yellow-500 bg-yellow-900/20 text-yellow-300'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  Futures
                </button>
              </div>
            </div>

            {/* Leverage Slider */}
            {tradeForm.tradeType === 'futures' && (
              <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
                <h2 className="text-xl font-bold mb-4 flex items-center">
                  <BoltIcon className="h-6 w-6 mr-2 text-yellow-500" />
                  Leverage
                </h2>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={tradeForm.leverage}
                    onChange={(e) => setTradeForm(prev => ({...prev, leverage: parseInt(e.target.value)}))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-2">
                    <span>1x</span>
                    <span className="font-bold text-lg text-white">{tradeForm.leverage}x</span>
                    <span>100x</span>
                  </div>
              </div>
            )}

            {/* Trade Side */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h2 className="text-xl font-bold mb-4">Trade Side</h2>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setTradeForm(prev => ({ ...prev, side: 'buy' }))}
                  className={`p-4 border rounded-lg font-semibold transition-colors ${
                    tradeForm.side === 'buy'
                      ? 'border-green-500 bg-green-900/20 text-green-300'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  {tradeForm.tradeType === 'futures' ? 'LONG' : 'BUY'}
                </button>
                <button
                  type="button"
                  onClick={() => setTradeForm(prev => ({ ...prev, side: 'sell' }))}
                  className={`p-4 border rounded-lg font-semibold transition-colors ${
                    tradeForm.side === 'sell'
                      ? 'border-red-500 bg-red-900/20 text-red-300'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  {tradeForm.tradeType === 'futures' ? 'SHORT' : 'SELL'}
                </button>
              </div>
            </div>
            
            {/* Order Details */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h2 className="text-xl font-bold mb-4">Order Details</h2>
              <div className="space-y-4 text-white">
                {/* Order Type */}
                <div className="flex items-center space-x-4">
                  <span className="font-semibold">Type:</span>
                  <button type="button" onClick={() => setTradeForm(prev => ({...prev, orderType: 'market'}))} className={`px-4 py-2 rounded-md text-sm ${isMarketOrder ? 'bg-blue-600' : 'bg-gray-700'}`}>Market</button>
                  <button type="button" onClick={() => setTradeForm(prev => ({...prev, orderType: 'limit'}))} className={`px-4 py-2 rounded-md text-sm ${!isMarketOrder ? 'bg-blue-600' : 'bg-gray-700'}`}>Limit</button>
                </div>

                {/* Price (for limit orders) */}
                {!isMarketOrder && (
                    <div>
                    <label htmlFor="price" className="block text-sm font-medium text-gray-400 mb-1">Price (USDT)</label>
                    <input
                      type="number"
                      id="price"
                      value={tradeForm.price || ''}
                      onChange={(e) => handlePriceChange(parseFloat(e.target.value))}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 focus:ring-2 focus:ring-green-500"
                      placeholder="Enter price"
                    />
                  </div>
                )}
                
                {/* Amount */}
                <div>
                  <label htmlFor="amount" className="block text-sm font-medium text-gray-400 mb-1">Amount ({tradeForm.pair.split('/')[0]})</label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.001"
                    value={tradeForm.amount}
                    onChange={(e) => handleAmountChange(parseFloat(e.target.value))}
                    className="w-full bg-gray-700 text-white p-3 rounded-lg border border-gray-600 focus:ring-green-500 focus:border-green-500"
                    placeholder="0.00"
                  />
                </div>

                {/* Stop Loss */}
                <div>
                  <label htmlFor="stopLoss" className="block text-sm font-medium text-gray-400 mb-1">Stop Loss (USDT)</label>
                  <input
                    type="number"
                    id="stopLoss"
                    step="0.01"
                    min="0"
                    value={tradeForm.stopLoss || ''}
                    onChange={(e) => {
                      const value = e.target.value;
                      const parsedValue = value === '' ? undefined : parseFloat(value);
                      setTradeForm(prev => ({...prev, stopLoss: parsedValue}));
                    }}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 focus:ring-2 focus:ring-red-500"
                    placeholder="Optional"
                  />
                </div>

              </div>
            </div>

            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 text-white">
              <h2 className="text-xl font-bold mb-4">Order Summary</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total</span>
                  <span className="font-semibold">{tradeForm.total.toFixed(2)} USDT</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Fees (approx.)</span>
                  <span className="font-semibold">~{(tradeForm.total * 0.001).toFixed(4)} USDT</span>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !tradeForm.amount}
              className="w-full p-4 bg-green-600 rounded-lg font-bold text-lg hover:bg-green-700 transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isLoading ? 'Executing...' : `Submit ${tradeForm.side.toUpperCase()} Order`}
            </button>
          </form>

          {/* Right-side panel for order book/charts - Placeholder */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 text-white">
             <h2 className="text-xl font-bold mb-4">Market Data</h2>
             <p className="text-gray-500">Charts and order book data will be displayed here.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
