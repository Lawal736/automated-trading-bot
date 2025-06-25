"use client";

import { useBacktestStore } from '../../../lib/store';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

// Define a more specific type for indicator data if possible
type IndicatorData = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  [key: string]: any; // Allow other string keys
};

// Define Trade type to match backend
type Trade = {
  entry_date: string;
  exit_date: string | null;
  entry_price: number;
  exit_price: number | null;
  pnl: number;
  pnl_percent: number;
  side: string;
  condition_met?: boolean;
};

export default function BacktestDetailsPage() {
  const router = useRouter();
  const { backtestResult } = useBacktestStore();
  const [indicatorColumns, setIndicatorColumns] = useState<string[]>([]);

  useEffect(() => {
    if (backtestResult && backtestResult.indicator_data.length > 0) {
      // Dynamically determine columns from the first row of indicator data
      const firstRow = backtestResult.indicator_data[0];
      const columns = Object.keys(firstRow);
      setIndicatorColumns(columns);
    }
  }, [backtestResult]);

  if (!backtestResult) {
    return (
      <div className="container mx-auto p-4">
        <p className="text-white">Loading backtest results...</p>
      </div>
    );
  }

  // Type trades as Trade[]
  const { trades, indicator_data } = backtestResult as { trades: Trade[]; indicator_data: IndicatorData[] };

  return (
    <div className="container mx-auto p-4 max-w-7xl">
      <h1 className="text-3xl font-bold mb-6 text-white">Detailed Backtest Results</h1>
      
      {/* Trades Table */}
      <div className="bg-gray-800 p-6 rounded-lg mb-8">
        <h2 className="text-2xl font-semibold mb-4 text-white">Trade Log</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left text-gray-300">
            <thead className="text-xs text-gray-400 uppercase bg-gray-700">
              <tr>
                <th scope="col" className="px-6 py-3">Entry Date</th>
                <th scope="col" className="px-6 py-3">Exit Date</th>
                <th scope="col" className="px-6 py-3">Side</th>
                <th scope="col" className="px-6 py-3">Entry Price</th>
                <th scope="col" className="px-6 py-3">Exit Price</th>
                <th scope="col" className="px-6 py-3">PnL ($)</th>
                <th scope="col" className="px-6 py-3">PnL (%)</th>
                <th scope="col" className="px-6 py-3">Condition Met</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, index) => (
                <tr key={index} className="bg-gray-800 border-b border-gray-700 hover:bg-gray-600">
                  <td className="px-6 py-4">{trade.entry_date}</td>
                  <td className="px-6 py-4">{trade.exit_date}</td>
                  <td className="px-6 py-4 capitalize">{trade.side}</td>
                  <td className="px-6 py-4">${trade.entry_price.toFixed(2)}</td>
                  <td className="px-6 py-4">${trade.exit_price?.toFixed(2)}</td>
                  <td className={`px-6 py-4 ${trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {trade.pnl.toFixed(2)}
                  </td>
                  <td className={`px-6 py-4 ${trade.pnl_percent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {trade.pnl_percent.toFixed(2)}%
                  </td>
                  <td className="px-6 py-4 text-center">
                    <input type="checkbox" disabled checked={!!trade.condition_met} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Indicator Data Table */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-2xl font-semibold mb-4 text-white">Indicator & Market Data</h2>
        <div className="overflow-x-auto" style={{ maxHeight: '600px' }}>
          <table className="min-w-full text-sm text-left text-gray-300">
            <thead className="text-xs text-gray-400 uppercase bg-gray-700 sticky top-0">
              <tr>
                {indicatorColumns.map((col) => (
                  <th key={col} scope="col" className="px-6 py-3 whitespace-nowrap">{col.replace(/_/g, ' ').toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {indicator_data.map((row: IndicatorData, index) => (
                <tr key={index} className="bg-gray-800 border-b border-gray-700 hover:bg-gray-600">
                  {indicatorColumns.map((col) => (
                    <td key={col} className="px-6 py-4 whitespace-nowrap">
                      {typeof row[col] === 'number' ? row[col].toFixed(4) : row[col]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
       <button
            onClick={() => router.back()}
            className="mt-6 bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg transition duration-300"
          >
            Back
          </button>
    </div>
  );
} 