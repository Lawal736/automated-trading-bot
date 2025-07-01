"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  UsersIcon,
  CurrencyDollarIcon,
  ComputerDesktopIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  UserGroupIcon,
  CogIcon,
  DocumentTextIcon,
  BoltIcon,
  KeyIcon,
} from '@heroicons/react/24/outline';
import { getAdminOverview, AdminOverview } from '../../../lib/admin';
import ProtectedRoute from '../../components/ProtectedRoute';
import PasswordChangeModal from '../../../components/PasswordChangeModal';

const StatCard = ({ 
  title, 
  value, 
  icon, 
  subtitle, 
  color = "blue",
  trend 
}: { 
  title: string; 
  value: string | number; 
  icon: React.ReactNode; 
  subtitle?: string;
  color?: string;
  trend?: { value: number; isPositive: boolean };
}) => {
  const colorClasses = {
    blue: "text-blue-500 bg-blue-500/10",
    green: "text-green-500 bg-green-500/10",
    red: "text-red-500 bg-red-500/10",
    yellow: "text-yellow-500 bg-yellow-500/10",
    purple: "text-purple-500 bg-purple-500/10",
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <div className={`p-3 rounded-lg ${colorClasses[color as keyof typeof colorClasses]}`}>
            {icon}
          </div>
          <div className="ml-4">
            <p className="text-sm text-gray-400">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
          </div>
        </div>
        {trend && (
          <div className={`flex items-center text-sm ${trend.isPositive ? 'text-green-500' : 'text-red-500'}`}>
            {trend.isPositive ? (
              <ArrowTrendingUpIcon className="h-4 w-4 mr-1" />
            ) : (
              <ArrowTrendingDownIcon className="h-4 w-4 mr-1" />
            )}
            {trend.value}%
          </div>
        )}
      </div>
    </div>
  );
};

export default function AdminDashboard() {
  const router = useRouter();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const fetchOverview = async () => {
      try {
        const data = await getAdminOverview(token);
        setOverview(data);
      } catch (err: any) {
        if (err.message.includes('403')) {
          setError('Access denied. Admin privileges required.');
        } else {
          setError(err?.response?.data?.detail || 'Failed to fetch admin data.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900 text-red-200 p-6 rounded-lg border border-red-700">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-6 w-6 mr-3" />
              <h2 className="text-xl font-bold">Access Error</h2>
            </div>
            <p className="mt-2">{error}</p>
            <button
              onClick={() => router.push('/dashboard')}
              className="mt-4 bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!overview) {
    return null;
  }

  const successRate = overview.trades.total > 0 
    ? ((overview.trades.filled / overview.trades.total) * 100).toFixed(1)
    : 0;

  return (
    <ProtectedRoute requireAdmin={true}>
      <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold flex items-center">
                  <CogIcon className="h-8 w-8 mr-3 text-indigo-400" />
                  Admin Dashboard
                </h1>
                <p className="text-gray-400 mt-2">System overview and analytics</p>
              </div>
              <button
                onClick={() => setShowPasswordModal(true)}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <KeyIcon className="h-5 w-5 mr-2" />
                Change Password
              </button>
            </div>
          </div>

          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
              title="Total Users"
              value={overview.users.total}
              subtitle={`${overview.users.active} active`}
              icon={<UsersIcon className="h-6 w-6" />}
              color="blue"
            />
            <StatCard
              title="Total Trades"
              value={overview.trades.total}
              subtitle={`${overview.trades.recent_7_days} this week`}
              icon={<CurrencyDollarIcon className="h-6 w-6" />}
              color="green"
            />
            <StatCard
              title="Active Bots"
              value={overview.bots.active}
              subtitle={`${overview.bots.total} total`}
              icon={<ComputerDesktopIcon className="h-6 w-6" />}
              color="purple"
            />
            <StatCard
              title="Success Rate"
              value={`${successRate}%`}
              subtitle={`${overview.trades.filled} filled / ${overview.trades.rejected} rejected`}
              icon={<ChartBarIcon className="h-6 w-6" />}
              color="yellow"
            />
          </div>

          {/* Detailed Stats */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Trading Statistics */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h2 className="text-xl font-bold mb-4 flex items-center">
                <CurrencyDollarIcon className="h-6 w-6 mr-2 text-green-400" />
                Trading Statistics
              </h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Buy Trades</p>
                    <p className="text-lg font-bold text-green-400">{overview.trades.buy}</p>
                  </div>
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Sell Trades</p>
                    <p className="text-lg font-bold text-red-400">{overview.trades.sell}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Spot Trades</p>
                    <p className="text-lg font-bold">{overview.trades.spot}</p>
                  </div>
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Futures Trades</p>
                    <p className="text-lg font-bold">{overview.trades.futures}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Manual Trades</p>
                    <p className="text-lg font-bold">{overview.trades.manual}</p>
                  </div>
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Bot Trades</p>
                    <p className="text-lg font-bold">{overview.trades.bot_trades}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* System Status */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h2 className="text-xl font-bold mb-4 flex items-center">
                <CogIcon className="h-6 w-6 mr-2 text-blue-400" />
                System Status
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Exchange Connections</span>
                  <div className="flex items-center">
                    <span className="text-white font-bold">{overview.exchanges.active_connections}</span>
                    <span className="text-gray-500 ml-1">/ {overview.exchanges.total_connections}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Open Positions</span>
                  <div className="flex items-center">
                    <span className="text-white font-bold">{overview.positions.open}</span>
                    <span className="text-gray-500 ml-1">/ {overview.positions.total}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Strategies</span>
                  <span className="text-white font-bold">{overview.strategies.total}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Recent Activities</span>
                  <span className="text-white font-bold">{overview.activity.recent_7_days}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <BoltIcon className="h-6 w-6 mr-2 text-yellow-400" />
              Quick Actions
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => router.push('/dashboard/admin/trades')}
                className="bg-blue-600 text-white p-4 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <DocumentTextIcon className="h-6 w-6 mb-2" />
                <p className="font-semibold">View All Trades</p>
                <p className="text-sm text-blue-200">{overview.trades.total} total trades</p>
              </button>
              <button
                onClick={() => router.push('/dashboard/admin/users')}
                className="bg-green-600 text-white p-4 rounded-lg hover:bg-green-700 transition-colors"
              >
                <UserGroupIcon className="h-6 w-6 mb-2" />
                <p className="font-semibold">Manage Users</p>
                <p className="text-sm text-green-200">{overview.users.total} total users</p>
              </button>
              <button
                onClick={() => router.push('/dashboard/admin/bots')}
                className="bg-purple-600 text-white p-4 rounded-lg hover:bg-purple-700 transition-colors"
              >
                <ComputerDesktopIcon className="h-6 w-6 mb-2" />
                <p className="font-semibold">Monitor Bots</p>
                <p className="text-sm text-purple-200">{overview.bots.active} active bots</p>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Password Change Modal */}
      <PasswordChangeModal
        isOpen={showPasswordModal}
        onClose={() => setShowPasswordModal(false)}
        onSuccess={() => {
          // Could add additional success handling here if needed
        }}
      />
    </ProtectedRoute>
  );
} 