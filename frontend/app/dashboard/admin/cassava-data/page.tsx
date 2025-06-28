"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  TableCellsIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
  CalendarIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import ProtectedRoute from '../../../components/ProtectedRoute';

interface CassavaTrendData {
  id: number;
  date: string;
  symbol: string;
  ema_10: number;
  ema_8: number;
  ema_20: number;
  ema_15: number;
  ema_25: number;
  ema_5: number;
  di_plus: number;
  top_fractal: number | null;
  trading_condition: 'BUY' | 'SHORT' | 'HOLD';
  created_at: string;
  price?: number;
}

interface CassavaDataResponse {
  data: CassavaTrendData[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export default function CassavaDataPage() {
  const router = useRouter();
  const [data, setData] = useState<CassavaTrendData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 50;
  
  // Filters
  const [symbol, setSymbol] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [tradingCondition, setTradingCondition] = useState('');
  const [symbols, setSymbols] = useState<string[]>([]);

  // Track if filters have changed
  const [filtersChanged, setFiltersChanged] = useState(false);

  // Load filters from localStorage on mount
  useEffect(() => {
    const savedFilters = localStorage.getItem('cassava_filters');
    if (savedFilters) {
      const { symbol, startDate, endDate, tradingCondition } = JSON.parse(savedFilters);
      setSymbol(symbol || '');
      setStartDate(startDate || '');
      setEndDate(endDate || '');
      setTradingCondition(tradingCondition || '');
    }
  }, []);

  // Save filters to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('cassava_filters', JSON.stringify({ symbol, startDate, endDate, tradingCondition }));
  }, [symbol, startDate, endDate, tradingCondition]);

  // Fetch symbols on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }
    fetchSymbols(token);
  }, [router]);

  // Fetch data only when 'Apply' is clicked or page changes
  const fetchData = async (token: string, pageOverride?: number) => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({
        page: (pageOverride || page).toString(),
        size: PAGE_SIZE.toString(),
      });
      if (symbol && symbol !== '') params.append('symbol', symbol);
      if (startDate && startDate !== '') params.append('start_date', startDate);
      if (endDate && endDate !== '') params.append('end_date', endDate);
      if (tradingCondition && tradingCondition !== '') params.append('trading_condition', tradingCondition);
      const apiUrl = `/api/v1/cassava-data/cassava-trend-data?${params}`;
      console.log('Fetching Cassava data from:', apiUrl);
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const result: CassavaDataResponse = await response.json();
        setData(result.data);
        setTotalPages(result.total_pages);
        setTotal(result.total);
      } else {
        const errorText = await response.text();
        setError('Failed to fetch data: ' + errorText);
        console.error('API error:', errorText);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch Cassava data.');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handler for Apply button
  const handleApplyFilters = async () => {
    setPage(1);
    setFiltersChanged(false);
    const token = localStorage.getItem('access_token');
    if (token) {
      await fetchData(token, 1);
    }
  };

  // Fetch data on page change (but not on filter change)
  useEffect(() => {
    if (!filtersChanged) {
      const token = localStorage.getItem('access_token');
      if (token) fetchData(token, page);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  // Mark filters as changed when any filter changes
  const onFilterChange = (setter: (v: any) => void) => (e: any) => {
    setter(e.target.value);
    setFiltersChanged(true);
  };

  const fetchSymbols = async (token: string) => {
    try {
      const response = await fetch(`/api/v1/cassava-data/cassava-trend-data/symbols`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const result = await response.json();
        setSymbols(result.symbols);
      }
    } catch (error) {
      console.error('Error fetching symbols:', error);
    }
  };

  const exportData = async (format: 'csv' | 'excel') => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const params = new URLSearchParams({
        format,
      });
      
      if (symbol) params.append('symbol', symbol);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (tradingCondition) params.append('trading_condition', tradingCondition);

      const response = await fetch(`/api/v1/cassava-data/cassava-trend-data/export?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cassava_trend_data.${format === 'csv' ? 'csv' : 'xlsx'}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error exporting data:', error);
    }
  };

  const getConditionColor = (condition: string) => {
    switch (condition) {
      case 'BUY':
        return 'text-green-400 bg-green-400/10';
      case 'SHORT':
        return 'text-red-400 bg-red-400/10';
      case 'HOLD':
        return 'text-yellow-400 bg-yellow-400/10';
      default:
        return 'text-gray-400 bg-gray-400/10';
    }
  };

  const formatNumber = (value: number | null | undefined) =>
    value !== null && value !== undefined
      ? value.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 })
      : '-';

  if (loading && data.length === 0) {
    return (
      <ProtectedRoute requireAdmin={true}>
        <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute requireAdmin={true}>
      <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold flex items-center">
                  <TableCellsIcon className="h-8 w-8 mr-3 text-indigo-400" />
                  Cassava BOT Data
                </h1>
                <p className="text-gray-400 mt-2">Daily technical indicators and trading conditions for all pairs</p>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => exportData('csv')}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center"
                >
                  <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                  Export CSV
                </button>
                <button
                  onClick={() => exportData('excel')}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center"
                >
                  <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                  Export Excel
                </button>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-6">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <FunnelIcon className="h-6 w-6 mr-2 text-blue-400" />
              Filters
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                <select
                  value={symbol}
                  onChange={onFilterChange(setSymbol)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                >
                  <option value="">All Symbols</option>
                  {symbols.map((sym) => (
                    <option key={sym} value={sym}>{sym}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={onFilterChange(setStartDate)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={onFilterChange(setEndDate)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Condition</label>
                <select
                  value={tradingCondition}
                  onChange={onFilterChange(setTradingCondition)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                >
                  <option value="">All Conditions</option>
                  <option value="BUY">BUY</option>
                  <option value="SHORT">SHORT</option>
                  <option value="HOLD">HOLD</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={handleApplyFilters}
                disabled={!filtersChanged || loading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-semibold disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Apply'}
              </button>
            </div>
          </div>

          {/* Results Info */}
          <div className="flex justify-between items-center mb-4">
            <p className="text-gray-400">
              Showing {data.length} of {total} records
            </p>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white px-3 py-1 rounded-lg"
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
              <span className="text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white px-3 py-1 rounded-lg"
              >
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Data Table */}
          <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs whitespace-nowrap">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">Date</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">Symbol</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">Price</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">EMA 5</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">EMA 8</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">EMA 10</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">EMA 15</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">EMA 20</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">EMA 25</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">DI+</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">Top Fractal</th>
                    <th className="px-1 py-1 text-left font-medium text-gray-300">Condition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {data.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-700/50">
                      <td className="px-1 py-1 text-gray-300">{new Date(item.date).toLocaleDateString()}</td>
                      <td className="px-1 py-1 font-medium text-white">{item.symbol}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.price)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.ema_5)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.ema_8)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.ema_10)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.ema_15)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.ema_20)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.ema_25)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.di_plus)}</td>
                      <td className="px-1 py-1 text-gray-300">{formatNumber(item.top_fractal)}</td>
                      <td className="px-1 py-1">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getConditionColor(item.trading_condition)}`}>
                          {item.trading_condition}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {data.length === 0 && !loading && (
            <div className="text-center py-8">
              <p className="text-gray-400">No data found with the current filters.</p>
            </div>
          )}

          {error && (
            <div className="bg-red-800 text-red-200 px-4 py-2 rounded mb-4">
              {error}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
} 