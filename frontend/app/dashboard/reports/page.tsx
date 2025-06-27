"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeftIcon, DocumentChartBarIcon, ArrowUpCircleIcon, ArrowDownCircleIcon, ScaleIcon, ChartPieIcon, CurrencyDollarIcon, ClockIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { getReport, ReportData } from '../../../lib/reports';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const StatCard = ({ title, value, icon, a_value, color = "text-white" }: { title: string, value: string, icon: React.ReactNode, a_value?: string, color?: string }) => (
  <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
    <div className="flex items-center">
      {icon}
      <div className="ml-4">
        <p className="text-sm text-gray-400">{title}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        {a_value && <p className="text-xs text-gray-500">{a_value}</p>}
      </div>
    </div>
  </div>
);

export default function ReportsPage() {
  const router = useRouter();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const fetchReport = async () => {
      try {
        const data = await getReport(token);
        setReport(data);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to fetch report data.');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [router]);
  
  const formatPnl = (pnl) => {
    const value = pnl.toFixed(2);
    return pnl >= 0 ? `$${value}`: `-$${Math.abs(value)}`;
  }
  
  const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;

  const formatNumber = (value) => value.toLocaleString();

  // Prepare data for pie chart
  const getTradeTypeData = () => {
    if (!report?.trade_stats) return [];
    return [
      { name: 'Spot', value: report.trade_stats.spot_trades, color: '#3B82F6' },
      { name: 'Futures', value: report.trade_stats.futures_trades, color: '#F59E0B' },
    ].filter(item => item.value > 0);
  };

  const getTradeSideData = () => {
    if (!report?.trade_stats) return [];
    return [
      { name: 'Buy', value: report.trade_stats.buy_trades, color: '#10B981' },
      { name: 'Sell', value: report.trade_stats.sell_trades, color: '#EF4444' },
    ].filter(item => item.value > 0);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <button
          onClick={() => router.back()}
          className="flex items-center space-x-2 text-gray-400 hover:text-white mb-6"
        >
          <ArrowLeftIcon className="h-5 w-5" />
          <span>Back to Dashboard</span>
        </button>

        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-6 border-b border-gray-700 flex items-center space-x-3">
            <DocumentChartBarIcon className="h-8 w-8 text-indigo-400" />
            <h1 className="text-2xl font-bold">Trading Reports</h1>
          </div>
          
          {loading && <div className="p-6 text-center">Loading report...</div>}
          {error && <div className="p-6 text-center text-red-500">{error}</div>}

          {report && !loading && !error && (
            <div className="p-6 space-y-8">
              {/* Key Stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard 
                  title="Total Net P&L"
                  value={formatPnl(report.total_pnl)}
                  icon={<ScaleIcon className={`h-8 w-8 ${report.total_pnl >= 0 ? 'text-green-500': 'text-red-500'}`} />}
                  color={report.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}
                />
                <StatCard 
                  title="Success Rate"
                  value={formatPercent(report.trade_stats?.success_rate || 0)}
                  a_value={`${report.total_trades} total trades`}
                  icon={<ChartPieIcon className="h-8 w-8 text-blue-500" />}
                  color="text-blue-400"
                />
                <StatCard 
                  title="Average Profit"
                  value={formatPnl(report.avg_profit)}
                  icon={<ArrowUpCircleIcon className="h-8 w-8 text-green-500" />}
                  color="text-green-400"
                />
                <StatCard 
                  title="Average Loss"
                  value={formatPnl(report.avg_loss)}
                  icon={<ArrowDownCircleIcon className="h-8 w-8 text-red-500" />}
                  color="text-red-400"
                />
              </div>

              {/* Trade Statistics */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Trade Counts */}
                <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <DocumentChartBarIcon className="h-6 w-6 mr-2 text-blue-400" />
                    Trade Statistics
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-800 p-4 rounded">
                      <div className="flex items-center">
                        <CheckCircleIcon className="h-5 w-5 text-green-400 mr-2" />
                        <div>
                          <p className="text-sm text-gray-400">Filled</p>
                          <p className="text-lg font-bold text-green-400">{formatNumber(report.trade_stats?.filled_trades || 0)}</p>
                        </div>
                      </div>
                    </div>
                    <div className="bg-gray-800 p-4 rounded">
                      <div className="flex items-center">
                        <XCircleIcon className="h-5 w-5 text-red-400 mr-2" />
                        <div>
                          <p className="text-sm text-gray-400">Rejected</p>
                          <p className="text-lg font-bold text-red-400">{formatNumber(report.trade_stats?.rejected_trades || 0)}</p>
                        </div>
                      </div>
                    </div>
                    <div className="bg-gray-800 p-4 rounded">
                      <div className="flex items-center">
                        <ClockIcon className="h-5 w-5 text-yellow-400 mr-2" />
                        <div>
                          <p className="text-sm text-gray-400">Pending</p>
                          <p className="text-lg font-bold text-yellow-400">{formatNumber(report.trade_stats?.pending_trades || 0)}</p>
                        </div>
                      </div>
                    </div>
                    <div className="bg-gray-800 p-4 rounded">
                      <div className="flex items-center">
                        <CurrencyDollarIcon className="h-5 w-5 text-purple-400 mr-2" />
                        <div>
                          <p className="text-sm text-gray-400">Total Volume</p>
                          <p className="text-lg font-bold text-purple-400">${formatNumber(report.trade_stats?.total_volume || 0)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trade Type Distribution */}
                <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
                  <h3 className="text-lg font-semibold mb-4">Trade Type Distribution</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={getTradeTypeData()}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {getTradeTypeData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Trade Side Distribution */}
              <div className="bg-gray-900 p-6 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Buy vs Sell Distribution</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={getTradeSideData()}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {getTradeSideData().map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* P&L Chart */}
              <div className="h-96 bg-gray-900 p-4 rounded-lg border border-gray-700">
                <h3 className="text-lg font-semibold mb-4">P&L Over Time</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={report.daily_pnl_data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
                    <XAxis dataKey="day" stroke="#A0AEC0" />
                    <YAxis stroke="#A0AEC0" tickFormatter={formatPnl} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1A202C', border: '1px solid #4A5568' }} 
                      labelStyle={{ color: '#E2E8F0' }}
                      formatter={(value) => formatPnl(value)}
                    />
                    <Legend wrapperStyle={{ color: '#E2E8F0' }} />
                    <Line type="monotone" dataKey="pnl" stroke="#48BB78" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 8 }} name="Daily P&L" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Strategy Performance */}
              <div>
                <h3 className="text-lg font-semibold mb-4">Performance by Strategy</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-gray-900 border border-gray-700">
                    <thead>
                      <tr className="bg-gray-700">
                        <th className="py-3 px-4 text-left">Strategy</th>
                        <th className="py-3 px-4 text-right">Total P&L</th>
                        <th className="py-3 px-4 text-right">Trades</th>
                        <th className="py-3 px-4 text-right">Win/Loss Ratio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.strategy_performance.map((s, index) => (
                        <tr key={index} className="border-b border-gray-700 hover:bg-gray-800">
                          <td className="py-3 px-4">{s.strategy_name}</td>
                          <td className={`py-3 px-4 text-right font-mono ${s.total_pnl >= 0 ? 'text-green-400': 'text-red-400'}`}>{formatPnl(s.total_pnl)}</td>
                          <td className="py-3 px-4 text-right font-mono">{s.total_trades}</td>
                          <td className="py-3 px-4 text-right font-mono">{formatPercent(s.win_loss_ratio)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
} 