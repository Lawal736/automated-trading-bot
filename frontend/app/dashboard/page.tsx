"use client";

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ComputerDesktopIcon,
  CurrencyDollarIcon,
  PlayIcon,
  StopIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowTrendingUpIcon as TrendingUpIcon,
  ArrowsRightLeftIcon as SwitchHorizontalIcon,
  ArrowDownIcon,
  ArrowUpIcon,
  ArrowPathIcon as RefreshIcon,
  XMarkIcon,
  DocumentTextIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { getBots, startBot, stopBot, deleteBot } from '../../lib/bots';
import { getActivities } from '../../lib/activities';
import { getPortfolio, PortfolioData } from '../../lib/portfolio';
import { BotStatus, RecentActivity } from '../../lib/types';
import PositionsModal from '../../components/PositionsModal';

// Cache keys
const CACHE_KEYS = {
  PORTFOLIO: 'dashboard_portfolio',
  BOTS: 'dashboard_bots',
  ACTIVITIES: 'dashboard_activities',
  LAST_UPDATE: 'dashboard_last_update'
};

// Cache expiry time (5 minutes)
const CACHE_EXPIRY = 5 * 60 * 1000;

export default function DashboardPage() {
  const [user, setUser] = useState<{ email?: string; username?: string } | null>(null);

  // Portfolio State
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [portfolioRefreshing, setPortfolioRefreshing] = useState(false);

  // Bots State
  const [bots, setBots] = useState<BotStatus[]>([]);
  const [botsLoading, setBotsLoading] = useState(false);
  const [botsError, setBotsError] = useState<string | null>(null);
  const [botsRefreshing, setBotsRefreshing] = useState(false);

  // Activities State
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [activitiesError, setActivitiesError] = useState<string | null>(null);
  const [activitiesRefreshing, setActivitiesRefreshing] = useState(false);

  // Delete Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [botToDelete, setBotToDelete] = useState<BotStatus | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Cache state
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [usingCachedData, setUsingCachedData] = useState(false);

  const [positionsModalOpen, setPositionsModalOpen] = useState(false);

  const router = useRouter();

  // Load cached data from localStorage
  const loadCachedData = useCallback(() => {
    const cachedPortfolio = localStorage.getItem(CACHE_KEYS.PORTFOLIO);
    const cachedBots = localStorage.getItem(CACHE_KEYS.BOTS);
    const cachedActivities = localStorage.getItem(CACHE_KEYS.ACTIVITIES);
    const lastUpdateTime = localStorage.getItem(CACHE_KEYS.LAST_UPDATE);

    let hasCache = false;

    if (cachedPortfolio) {
      try {
        setPortfolio(JSON.parse(cachedPortfolio));
        hasCache = true;
      } catch (e) {
        console.warn('Failed to parse cached portfolio:', e);
      }
    }

    if (cachedBots) {
      try {
        setBots(JSON.parse(cachedBots));
        hasCache = true;
      } catch (e) {
        console.warn('Failed to parse cached bots:', e);
      }
    }

    if (cachedActivities) {
      try {
        setActivities(JSON.parse(cachedActivities));
        hasCache = true;
      } catch (e) {
        console.warn('Failed to parse cached activities:', e);
      }
    }

    if (lastUpdateTime) {
      try {
        setLastUpdate(new Date(lastUpdateTime));
        hasCache = true;
      } catch (e) {
        console.warn('Failed to parse last update time:', e);
      }
    }

    if (hasCache) {
      setUsingCachedData(true);
    }

    return hasCache;
  }, []);

  // Save data to cache
  const saveToCache = useCallback((key: string, data: any) => {
    try {
      localStorage.setItem(key, JSON.stringify(data));
      localStorage.setItem(CACHE_KEYS.LAST_UPDATE, new Date().toISOString());
      setLastUpdate(new Date());
    } catch (e) {
      console.warn('Failed to save to cache:', e);
    }
  }, []);

  // Fetch Portfolio
  const fetchPortfolio = useCallback(async (showLoader = false) => {
    if (showLoader) setPortfolioLoading(true);
    setPortfolioRefreshing(true);
    setPortfolioError(null);

    try {
      const data = await getPortfolio();
      setPortfolio(data);
      saveToCache(CACHE_KEYS.PORTFOLIO, data);
      setUsingCachedData(false);
    } catch (err) {
      console.error('Failed to fetch portfolio:', err);
      setPortfolioError('Failed to refresh portfolio data.');
    } finally {
      setPortfolioLoading(false);
      setPortfolioRefreshing(false);
    }
  }, [saveToCache]);

  // Fetch Bots
  const fetchBots = useCallback(async (showLoader = false) => {
    if (showLoader) setBotsLoading(true);
    setBotsRefreshing(true);
    setBotsError(null);

    try {
      const data = await getBots();
      const transformedBots = data.map((bot: any) => ({
        ...bot,
        trading_pairs: Array.isArray(bot.trading_pairs) ? bot.trading_pairs : bot.trading_pairs.split(','),
      }));
      setBots(transformedBots);
      saveToCache(CACHE_KEYS.BOTS, transformedBots);
      setUsingCachedData(false);
    } catch (err) {
      console.error('Failed to fetch bots:', err);
      setBotsError('Failed to load trading bots.');
    } finally {
      setBotsLoading(false);
      setBotsRefreshing(false);
    }
  }, [saveToCache]);

  // Fetch Activities
  const fetchActivities = useCallback(async (showLoader = false) => {
    if (showLoader) setActivitiesLoading(true);
    setActivitiesRefreshing(true);
    setActivitiesError(null);

    try {
      const data = await getActivities();
      const recentActivities = data.slice(0, 5); // Get last 5 activities
      setActivities(recentActivities);
      saveToCache(CACHE_KEYS.ACTIVITIES, recentActivities);
      setUsingCachedData(false);
    } catch (err) {
      console.error('Failed to fetch activities:', err);
      setActivitiesError('Failed to load recent activities.');
    } finally {
      setActivitiesLoading(false);
      setActivitiesRefreshing(false);
    }
  }, [saveToCache]);

  // Fetch all data
  const fetchAllData = useCallback(async (showLoaders = false) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Fetch all data independently and in parallel
    await Promise.all([
      fetchPortfolio(showLoaders),
      fetchBots(showLoaders),
      fetchActivities(showLoaders)
    ]);
  }, [router, fetchPortfolio, fetchBots, fetchActivities]);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    
    // Load cached data first for instant display
    const hasCachedData = loadCachedData();
    
    // Check if cache is fresh (within 5 minutes)
    const lastUpdateTime = localStorage.getItem(CACHE_KEYS.LAST_UPDATE);
    const shouldRefresh = !lastUpdateTime || 
      (Date.now() - new Date(lastUpdateTime).getTime()) > CACHE_EXPIRY;

    // Fetch fresh data in background (show loaders only if no cache)
    fetchAllData(!hasCachedData || shouldRefresh);
  }, [loadCachedData, fetchAllData]);

  const handleStartBot = async (botId: number) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setBotsError('Authentication token not found.');
      return;
    }
    try {
      await startBot(botId);
      await Promise.all([fetchBots(), fetchPortfolio()]); // Refresh bots and portfolio
    } catch (error: any) {
      setBotsError(error?.response?.data?.detail || 'Failed to start bot.');
    }
  };

  const handleStopBot = async (botId: number) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setBotsError('Authentication token not found.');
      return;
    }
    try {
      await stopBot(botId);
      await Promise.all([fetchBots(), fetchPortfolio()]); // Refresh bots and portfolio
    } catch (error: any) {
      setBotsError(error?.response?.data?.detail || 'Failed to stop bot.');
    }
  };

  const handleDeleteBot = async () => {
    if (!botToDelete) return;
    
    const token = localStorage.getItem('access_token');
    if (!token) {
      setBotsError('Authentication token not found.');
      return;
    }
    
    setDeleteLoading(true);
    try {
      await deleteBot(botToDelete.id);
      setDeleteModalOpen(false);
      setBotToDelete(null);
      await Promise.all([fetchBots(), fetchPortfolio()]); // Refresh bots and portfolio
    } catch (error: any) {
      setBotsError(error?.response?.data?.detail || 'Failed to delete bot.');
    } finally {
      setDeleteLoading(false);
    }
  };

  const openDeleteModal = (bot: BotStatus) => {
    setBotToDelete(bot);
    setDeleteModalOpen(true);
  };

  const closeDeleteModal = () => {
    setDeleteModalOpen(false);
    setBotToDelete(null);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="flex justify-between items-center p-4 border-b border-gray-700">
        <div className="flex items-center">
          <h1 className="text-3xl font-bold">Trading Dashboard</h1>
          {(portfolioRefreshing || botsRefreshing || activitiesRefreshing) && (
            <RefreshIcon className="h-6 w-6 ml-4 text-gray-400 animate-spin" />
          )}
        </div>
        {usingCachedData && lastUpdate && (
          <div className="flex items-center text-sm text-gray-400">
            <ClockIcon className="h-4 w-4 mr-1" />
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Portfolio Overview */}
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-8">
          {portfolioLoading ? (
            <div className="text-center p-8">Loading portfolio...</div>
          ) : portfolioError && !portfolio ? (
            <div className="bg-red-900 text-red-200 p-3 rounded border border-red-700">{portfolioError}</div>
          ) : portfolio ? (
            <div>
              {portfolioError && (
                <div className="bg-yellow-900 text-yellow-200 p-2 rounded border border-yellow-700 mb-4 text-sm">
                  Could not refresh portfolio data. Displaying last known values.
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="flex items-center">
                  <CurrencyDollarIcon className="h-8 w-8 text-green-500 mr-4" />
                  <div>
                    <p className="text-sm text-gray-400">Total Balance</p>
                    <p className="text-2xl font-bold">${portfolio.total_balance.toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center">
                   <CurrencyDollarIcon className="h-8 w-8 text-blue-500 mr-4" />
                  <div>
                    <p className="text-sm text-gray-400">Daily P&L</p>
                    <p className={`text-2xl font-bold ${portfolio.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      ${portfolio.daily_pnl.toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center">
                  <TrendingUpIcon className="h-8 w-8 text-purple-500 mr-4" />
                  <button
                    className="focus:outline-none cursor-pointer group bg-transparent p-0 border-0 text-left"
                    style={{ background: 'none' }}
                    onClick={() => setPositionsModalOpen(true)}
                    aria-label="View Active Positions"
                  >
                    <p className="text-sm text-gray-400 group-hover:underline">Active Positions</p>
                    <p className="text-2xl font-bold text-blue-400 group-hover:underline">{portfolio.active_positions}</p>
                  </button>
                </div>
                <div className="flex items-center">
                  <SwitchHorizontalIcon className="h-8 w-8 text-yellow-500 mr-4" />
                  <div>
                    <p className="text-sm text-gray-400">Total Trades</p>
                    <p className="text-2xl font-bold">{portfolio.total_trades}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center p-8">No portfolio data available</div>
          )}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Trading Bots List */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center">
                  <h2 className="text-2xl font-bold">Trading Bots</h2>
                  {botsRefreshing && (
                    <RefreshIcon className="h-5 w-5 ml-2 text-gray-400 animate-spin" />
                  )}
                </div>
                <div className="flex space-x-2">
                  <Link href="/dashboard/trades">
                    <button className="bg-indigo-600 text-white px-4 py-2 rounded-lg flex items-center hover:bg-indigo-700">
                      <DocumentTextIcon className="h-5 w-5 mr-2" /> View Trades
                    </button>
                  </Link>
                  <Link href="/dashboard/create-bot">
                    <button className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center hover:bg-blue-700">
                      <PlusIcon className="h-5 w-5 mr-2" /> Create Bot
                    </button>
                  </Link>
                </div>
              </div>
              {botsLoading ? (
                <div className="text-center p-8">Loading bots...</div>
              ) : botsError && bots.length === 0 ? (
                <div className="bg-red-900 text-red-200 p-3 rounded border border-red-700">{botsError}</div>
              ) : (
                <div>
                  {botsError && (
                    <div className="bg-yellow-900 text-yellow-200 p-2 rounded border border-yellow-700 mb-4 text-sm">
                      Could not refresh bots. Displaying last known data.
                    </div>
                  )}
                  <div className="space-y-4">
                    {bots.length === 0 ? (
                      <div className="text-center p-8 text-gray-400">
                        No trading bots found. Create your first bot to get started.
                      </div>
                    ) : (
                      bots.map((bot) => (
                        <div key={bot.id} className="bg-gray-700/50 p-4 rounded-lg flex items-center justify-between border border-gray-600">
                          <div className="flex items-center">
                            <div className={`mr-4 p-2 rounded-full ${bot.is_active ? 'bg-green-500/20' : 'bg-gray-500/20'}`}>
                              <ComputerDesktopIcon className={`h-6 w-6 ${bot.is_active ? 'text-green-400' : 'text-gray-400'}`} />
                            </div>
                            <div>
                              <h3 className="font-bold text-lg">{bot.name} <span className={`text-xs font-medium px-2 py-1 rounded-full ${bot.is_active ? 'bg-green-800 text-green-200' : 'bg-gray-600 text-gray-200'}`}>{bot.is_active ? 'Active' : 'Inactive'}</span></h3>
                              <p className="text-sm text-gray-400">{bot.strategy_name}</p>
                              <div className="flex items-center space-x-4 mt-2 text-sm">
                                <span>Balance: <span className="font-semibold">${bot.current_balance.toLocaleString()}</span></span>
                                <span>Type: <span className="font-semibold">{bot.trade_type}</span></span>
                                <span>Pairs: <span className="font-semibold">{bot.trading_pairs.join(', ')}</span></span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Link href={`/dashboard/edit-bot/${bot.id}`}>
                              <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-lg">
                                <PencilIcon className="h-5 w-5" />
                              </button>
                            </Link>
                            <button 
                              onClick={() => openDeleteModal(bot)}
                              className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
                              title="Delete Bot"
                            >
                              <TrashIcon className="h-5 w-5" />
                            </button>
                            {!bot.is_active ? (
                              <button onClick={() => handleStartBot(bot.id)} className="bg-green-600 text-white px-4 py-2 rounded-lg flex items-center hover:bg-green-700">
                                <PlayIcon className="h-5 w-5 mr-1" /> Start
                              </button>
                            ) : (
                              <button onClick={() => handleStopBot(bot.id)} className="bg-red-600 text-white px-4 py-2 rounded-lg flex items-center hover:bg-red-700">
                                <StopIcon className="h-5 w-5 mr-1" /> Stop
                              </button>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Recent Activities */}
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center">
                <h2 className="text-2xl font-bold">Recent Activities</h2>
                {activitiesRefreshing && (
                  <RefreshIcon className="h-5 w-5 ml-2 text-gray-400 animate-spin" />
                )}
              </div>
              <button onClick={() => fetchActivities()} className="text-sm text-gray-400 hover:text-white flex items-center">
                <RefreshIcon className="h-4 w-4 mr-1" /> Refresh
              </button>
            </div>
            {activitiesLoading ? (
              <div className="text-center p-8">Loading activities...</div>
            ) : activitiesError && activities.length === 0 ? (
              <div className="bg-red-900 text-red-200 p-3 rounded border border-red-700">{activitiesError}</div>
            ) : (
              <div>
                {activitiesError && (
                  <div className="bg-yellow-900 text-yellow-200 p-2 rounded border border-yellow-700 mb-4 text-sm">
                    Could not refresh activities. Displaying last known data.
                  </div>
                )}
                <div className="space-y-4">
                  {activities.length === 0 ? (
                    <div className="text-center p-8 text-gray-400">
                      No recent activities found.
                    </div>
                  ) : (
                    activities.map((activity) => (
                      <div key={activity.id} className="flex items-start">
                        <div className="mr-4 mt-1">
                          <div className={`p-2 rounded-full ${
                            activity.type === 'trade' ? (activity.description.includes('BUY') || activity.description.includes('LONG') ? 'bg-green-500/20' : 'bg-red-500/20') :
                            activity.type === 'deposit' ? 'bg-blue-500/20' : 'bg-yellow-500/20'
                          }`}>
                            {activity.type === 'trade' ? <SwitchHorizontalIcon className={`h-5 w-5 ${activity.description.includes('BUY') || activity.description.includes('LONG') ? 'text-green-400' : 'text-red-400'}`} /> :
                             activity.type === 'deposit' ? <ArrowDownIcon className="h-5 w-5 text-blue-400" /> : <ArrowUpIcon className="h-5 w-5 text-yellow-400" />}
                          </div>
                        </div>
                        <div className="flex-grow">
                          <p className="font-semibold">{activity.description}</p>
                          <p className="text-sm text-gray-400">{new Date(activity.timestamp).toLocaleString()}</p>
                        </div>
                        <div className="text-right">
                          {activity.amount != null && (
                            <p className={`font-bold ${activity.amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {activity.amount >= 0 ? `+$${activity.amount.toLocaleString()}` : `-$${Math.abs(activity.amount).toLocaleString()}`}
                            </p>
                          )}
                          {activity.pnl !== null && typeof activity.pnl !== 'undefined' && (
                            <p className={`text-xs ${activity.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              P&L: ${activity.pnl.toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && botToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Delete Bot</h3>
              <button
                onClick={closeDeleteModal}
                className="text-gray-400 hover:text-white"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <p className="text-gray-300 mb-6">
              Are you sure you want to delete <span className="font-semibold text-white">{botToDelete.name}</span>? 
              This action cannot be undone and will permanently remove the bot and all its data.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={closeDeleteModal}
                className="flex-1 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700"
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteBot}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50"
                disabled={deleteLoading}
              >
                {deleteLoading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Positions Modal */}
      <PositionsModal 
        open={positionsModalOpen} 
        onClose={() => setPositionsModalOpen(false)} 
      />
    </div>
  );
}
