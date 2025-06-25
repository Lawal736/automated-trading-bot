import React, { useEffect, useState } from 'react';

interface Position {
  id: number;
  symbol: string;
  trade_type: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price?: number;
  leverage: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_pnl: number;
  stop_loss?: number;
  take_profit?: number;
  liquidation_price?: number;
  is_open: boolean;
  opened_at: string;
  closed_at?: string;
  updated_at?: string;
}

interface PositionsModalProps {
  open: boolean;
  onClose: () => void;
}

const PositionsModal: React.FC<PositionsModalProps> = ({ open, onClose }) => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('accessToken');
      fetch('/api/v1/portfolio/positions/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        redirect: 'follow',
      })
        .then((res) => {
          if (!res.ok) {
            console.error('Response status:', res.status);
            console.error('Response headers:', res.headers);
            throw new Error(`Failed to fetch positions: ${res.status} ${res.statusText}`);
          }
          return res.json();
        })
        .then((data) => {
          console.log('Positions data:', data);
          setPositions(data);
        })
        .catch((err) => {
          console.error('Fetch error:', err);
          setError(err.message);
        })
        .finally(() => setLoading(false));
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 w-full max-w-3xl relative">
        <button
          className="absolute top-2 right-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          onClick={onClose}
        >
          &times;
        </button>
        <h2 className="text-2xl font-bold mb-4">Open Positions</h2>
        {loading ? (
          <div>Loading...</div>
        ) : error ? (
          <div className="text-red-500">Could not load open positions. Please try again later.</div>
        ) : positions.length === 0 ? (
          <div className="text-gray-400">You have no open positions at this time.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  <th className="px-2 py-1">Symbol</th>
                  <th className="px-2 py-1">Side</th>
                  <th className="px-2 py-1">Qty</th>
                  <th className="px-2 py-1">Entry</th>
                  <th className="px-2 py-1">Current</th>
                  <th className="px-2 py-1">Leverage</th>
                  <th className="px-2 py-1">Unrealized PnL</th>
                  <th className="px-2 py-1">Total PnL</th>
                  <th className="px-2 py-1">Opened</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr key={pos.id} className="border-t">
                    <td className="px-2 py-1">{pos.symbol}</td>
                    <td className="px-2 py-1">{pos.side}</td>
                    <td className="px-2 py-1">{pos.quantity}</td>
                    <td className="px-2 py-1">{pos.entry_price}</td>
                    <td className="px-2 py-1">{pos.current_price ?? '-'}</td>
                    <td className="px-2 py-1">{pos.leverage}</td>
                    <td className="px-2 py-1">{pos.unrealized_pnl}</td>
                    <td className="px-2 py-1">{pos.total_pnl}</td>
                    <td className="px-2 py-1">{new Date(pos.opened_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PositionsModal; 