"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeftIcon, 
  ShieldCheckIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { toast } from "sonner";

interface ManagedTrade {
  trade_id: number;
  user_id: number;
  symbol: string;
  side: string;
  entry_price: number;
  quantity: number;
  current_stop_loss: number;
  position_id: number;
  created_at: string;
}

interface Activity {
  type: string;
  description: string;
  amount: number;
  timestamp: string;
}

interface StopLossStatus {
  managed_trades_count: number;
  managed_trades: ManagedTrade[];
  recent_activities: Activity[];
}

export default function ManualStopLossStatusPage() {
  const router = useRouter();
  const [status, setStatus] = useState<StopLossStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStopLossStatus();
  }, []);

  const fetchStopLossStatus = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem('access_token');
      if (!token) {
        setError('Authentication token not found.');
        return;
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/trades/manual-stop-loss-status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch stop loss status');
      }

      const data = await response.json();
      setStatus(data);
    } catch (error: any) {
      setError(error.message);
      toast.error('Failed to fetch stop loss status');
    } finally {
      setIsLoading(false);
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'MANUAL_STOP_LOSS_UPDATE':
        return <ShieldCheckIcon className="h-5 w-5 text-green-500" />;
      case 'MANUAL_EMA25_SETUP':
        return <CheckCircleIcon className="h-5 w-5 text-blue-500" />;
      case 'MANUAL_EMA25_SETUP_SCHEDULED':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const getActivityTitle = (type: string) => {
    switch (type) {
      case 'MANUAL_STOP_LOSS_UPDATE':
        return 'Stop Loss Updated';
      case 'MANUAL_EMA25_SETUP':
        return 'EMA25 Management Enabled';
      case 'MANUAL_EMA25_SETUP_SCHEDULED':
        return 'EMA25 Management Scheduled';
      default:
        return 'Activity';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <main className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <main className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
          <div className="text-center">
            <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Error</h2>
            <p className="text-gray-400">{error}</p>
            <button
              onClick={() => router.back()}
              className="mt-4 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
            >
              Go Back
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <main className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="mb-8">
          <button onClick={() => router.back()} className="flex items-center text-gray-400 hover:text-white mb-4">
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back
          </button>
          <h1 className="text-3xl font-bold flex items-center">
            <ShieldCheckIcon className="h-8 w-8 mr-3 text-green-400" />
            EMA25 Stop Loss Management
          </h1>
          <p className="text-gray-400 mt-2">
            Monitor your manual trades with automated EMA25 trailing stop loss management
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Managed Trades */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <ShieldCheckIcon className="h-6 w-6 mr-2 text-green-400" />
              Managed Trades ({status?.managed_trades_count || 0})
            </h2>
            
            {status?.managed_trades && status.managed_trades.length > 0 ? (
              <div className="space-y-4">
                {status.managed_trades.map((trade) => (
                  <div key={trade.trade_id} className="bg-gray-700 rounded-lg p-4 border border-gray-600">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{trade.symbol}</h3>
                        <p className="text-sm text-gray-400">Trade ID: {trade.trade_id}</p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        trade.side === 'buy' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      }`}>
                        {trade.side.toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-400">Entry Price</p>
                        <p className="font-semibold">${trade.entry_price.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Quantity</p>
                        <p className="font-semibold">{trade.quantity.toFixed(4)}</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Current Stop Loss</p>
                        <p className="font-semibold text-green-400">${trade.current_stop_loss.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Opened</p>
                        <p className="font-semibold">{formatDate(trade.created_at)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <ShieldCheckIcon className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400">No managed trades found</p>
                <p className="text-sm text-gray-500 mt-2">
                  Enable EMA25 trailing stop loss when placing manual trades to see them here
                </p>
              </div>
            )}
          </div>

          {/* Recent Activities */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <ClockIcon className="h-6 w-6 mr-2 text-blue-400" />
              Recent Activities
            </h2>
            
            {status?.recent_activities && status.recent_activities.length > 0 ? (
              <div className="space-y-4">
                {status.recent_activities.map((activity, index) => (
                  <div key={index} className="bg-gray-700 rounded-lg p-4 border border-gray-600">
                    <div className="flex items-start space-x-3">
                      {getActivityIcon(activity.type)}
                      <div className="flex-1">
                        <h3 className="font-semibold text-sm">
                          {getActivityTitle(activity.type)}
                        </h3>
                        <p className="text-gray-400 text-sm mt-1">
                          {activity.description}
                        </p>
                        <div className="flex justify-between items-center mt-2">
                          <span className="text-xs text-gray-500">
                            {formatDate(activity.timestamp)}
                          </span>
                          {activity.amount && (
                            <span className="text-xs font-semibold text-green-400">
                              ${activity.amount.toLocaleString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <ClockIcon className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400">No recent activities</p>
                <p className="text-sm text-gray-500 mt-2">
                  Stop loss updates and management activities will appear here
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Summary Stats */}
        <div className="mt-8 bg-gray-800 rounded-lg border border-gray-700 p-6">
          <h2 className="text-xl font-bold mb-4">Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {status?.managed_trades_count || 0}
              </div>
              <div className="text-sm text-gray-400">Active Managed Trades</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">
                {status?.recent_activities?.filter(a => a.type === 'MANUAL_STOP_LOSS_UPDATE').length || 0}
              </div>
              <div className="text-sm text-gray-400">Stop Loss Updates</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400">
                {status?.recent_activities?.filter(a => a.type === 'MANUAL_EMA25_SETUP').length || 0}
              </div>
              <div className="text-sm text-gray-400">EMA25 Setups</div>
            </div>
          </div>
        </div>

        {/* Refresh Button */}
        <div className="mt-8 text-center">
          <button
            onClick={fetchStopLossStatus}
            className="px-6 py-3 bg-green-600 rounded-lg font-semibold hover:bg-green-700 transition-colors"
          >
            Refresh Status
          </button>
        </div>
      </main>
    </div>
  );
} 
