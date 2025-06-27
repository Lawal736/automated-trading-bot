"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '../../../contexts/AuthContext';

interface User {
  id: number;
  email: string;
  username: string;
  subscription_tier: string;
  is_active: boolean;
  created_at: string;
  last_login?: string | null;
}

interface DetailedUser extends User {
  role: string;
  statistics: {
    trades: number;
    bots: number;
    connections: number;
    positions: number;
  };
  recent_trades: Array<{
    id: number;
    symbol: string;
    side: string;
    quantity: number;
    price: number;
    status: string;
    created_at: string;
    executed_price?: number;
  }>;
  recent_activities: Array<{
    id: number;
    type: string;
    description: string;
    amount: number;
    pnl: number;
    timestamp: string;
  }>;
}

export default function AdminUsersPage() {
  const { user: loggedInUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [selectedUser, setSelectedUser] = useState<DetailedUser | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    username: '',
    subscription_tier: '',
    is_active: true,
    role: ''
  });

  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch('/api/v1/admin/users', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to fetch users');
        const data = await res.json();
        setUsers(data.users || []);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  const handleDelete = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    setDeletingId(userId);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to delete user');
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err: any) {
      alert(err.message || 'Failed to delete user');
    } finally {
      setDeletingId(null);
    }
  };

  const handleView = async (userId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/v1/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch user details');
      const userData = await res.json();
      setSelectedUser(userData);
      setEditForm({
        username: userData.username,
        subscription_tier: userData.subscription_tier || '',
        is_active: userData.is_active,
        role: userData.role
      });
      setIsEditing(false);
      setIsModalOpen(true);
    } catch (err: any) {
      alert(err.message || 'Failed to fetch user details');
    }
  };

  const handleEdit = async (userId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/v1/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch user details');
      const userData = await res.json();
      setSelectedUser(userData);
      setEditForm({
        username: userData.username,
        subscription_tier: userData.subscription_tier || '',
        is_active: userData.is_active,
        role: userData.role
      });
      setIsEditing(true);
      setIsModalOpen(true);
    } catch (err: any) {
      alert(err.message || 'Failed to fetch user details');
    }
  };

  const handleSave = async () => {
    if (!selectedUser) return;
    
    // Only include 'role' if editing another user
    const isOwnAccount = loggedInUser && selectedUser.id === loggedInUser.id;
    const updatePayload = isOwnAccount
      ? {
          username: editForm.username,
          subscription_tier: editForm.subscription_tier,
          is_active: editForm.is_active,
        }
      : editForm;

    console.log('Saving user data:', {
      userId: selectedUser.id,
      updatePayload,
      isOwnAccount,
    });
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/v1/admin/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatePayload),
      });
      
      console.log('Response status:', res.status);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.log('Error response:', errorText);
        throw new Error(`Failed to update user: ${res.status} - ${errorText}`);
      }
      
      const responseData = await res.json();
      console.log('Success response:', responseData);
      
      // Update the user in the list
      setUsers(prev => prev.map(user => 
        user.id === selectedUser.id 
          ? { ...user, ...editForm }
          : user
      ));
      
      // Update the selected user
      setSelectedUser(prev => prev ? { ...prev, ...editForm } : null);
      setIsEditing(false);
    } catch (err: any) {
      console.error('Save error:', err);
      alert(err.message || 'Failed to update user');
    }
  };

  const handleCancel = () => {
    if (selectedUser) {
      setEditForm({
        username: selectedUser.username,
        subscription_tier: selectedUser.subscription_tier || '',
        is_active: selectedUser.is_active,
        role: selectedUser.role
      });
    }
    setIsEditing(false);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedUser(null);
    setIsEditing(false);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Manage Users</h1>
        
        {loading ? (
          <div>Loading...</div>
        ) : error ? (
          <div className="text-red-400">{error}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-gray-800 rounded-lg">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left">Email</th>
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Subscription</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Created</th>
                  <th className="px-4 py-2 text-left">Last Login</th>
                  <th className="px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b border-gray-700">
                    <td className="px-4 py-2">{user.email}</td>
                    <td className="px-4 py-2">{user.username}</td>
                    <td className="px-4 py-2">{user.subscription_tier || 'Free'}</td>
                    <td className="px-4 py-2">
                      {user.is_active ? 'Active' : 'Inactive'}
                    </td>
                    <td className="px-4 py-2">{user.created_at?.slice(0, 10)}</td>
                    <td className="px-4 py-2">{user.last_login ? user.last_login.slice(0, 10) : 'Never'}</td>
                    <td className="px-4 py-2 space-x-2">
                      <button 
                        className="px-2 py-1 bg-blue-600 rounded hover:bg-blue-700"
                        onClick={() => handleView(user.id)}
                      >
                        View
                      </button>
                      <button 
                        className="px-2 py-1 bg-yellow-600 rounded hover:bg-yellow-700"
                        onClick={() => handleEdit(user.id)}
                      >
                        Edit
                      </button>
                      <button
                        className="px-2 py-1 bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
                        onClick={() => handleDelete(user.id)}
                        disabled={deletingId === user.id}
                      >
                        {deletingId === user.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* User Detail Modal */}
        {isModalOpen && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">
                  {isEditing ? 'Edit User' : 'User Details'}
                </h2>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              {!isEditing ? (
                // View Mode
                <div className="space-y-6">
                  {/* Basic Info */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Email</label>
                      <p className="text-white">{selectedUser.email}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Username</label>
                      <p className="text-white">{selectedUser.username}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Role</label>
                      <p className="text-white">{selectedUser.role}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Subscription</label>
                      <p className="text-white">{selectedUser.subscription_tier || 'Free'}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Status</label>
                      <p className={`${selectedUser.is_active ? 'text-green-400' : 'text-red-400'}`}>
                        {selectedUser.is_active ? 'Active' : 'Inactive'}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Created</label>
                      <p className="text-white">{selectedUser.created_at?.slice(0, 19).replace('T', ' ')}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300">Last Login</label>
                      <p className="text-white">{selectedUser.last_login ? selectedUser.last_login.slice(0, 19).replace('T', ' ') : 'Never'}</p>
                    </div>
                  </div>

                  {/* Statistics */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Statistics</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-gray-700 p-3 rounded">
                        <div className="text-2xl font-bold text-blue-400">{selectedUser.statistics.trades}</div>
                        <div className="text-sm text-gray-300">Total Trades</div>
                      </div>
                      <div className="bg-gray-700 p-3 rounded">
                        <div className="text-2xl font-bold text-green-400">{selectedUser.statistics.bots}</div>
                        <div className="text-sm text-gray-300">Active Bots</div>
                      </div>
                      <div className="bg-gray-700 p-3 rounded">
                        <div className="text-2xl font-bold text-yellow-400">{selectedUser.statistics.connections}</div>
                        <div className="text-sm text-gray-300">Exchange Connections</div>
                      </div>
                      <div className="bg-gray-700 p-3 rounded">
                        <div className="text-2xl font-bold text-purple-400">{selectedUser.statistics.positions}</div>
                        <div className="text-sm text-gray-300">Open Positions</div>
                      </div>
                    </div>
                  </div>

                  {/* Recent Trades */}
                  {selectedUser.recent_trades.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Recent Trades</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full bg-gray-700 rounded">
                          <thead>
                            <tr>
                              <th className="px-3 py-2 text-left">Symbol</th>
                              <th className="px-3 py-2 text-left">Side</th>
                              <th className="px-3 py-2 text-left">Quantity</th>
                              <th className="px-3 py-2 text-left">Price</th>
                              <th className="px-3 py-2 text-left">Status</th>
                              <th className="px-3 py-2 text-left">Date</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedUser.recent_trades.map((trade) => (
                              <tr key={trade.id} className="border-b border-gray-600">
                                <td className="px-3 py-2">{trade.symbol}</td>
                                <td className={`px-3 py-2 ${trade.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                                  {trade.side.toUpperCase()}
                                </td>
                                <td className="px-3 py-2">{trade.quantity}</td>
                                <td className="px-3 py-2">${trade.status === 'filled' ? trade.executed_price : trade.price}</td>
                                <td className="px-3 py-2">{trade.status}</td>
                                <td className="px-3 py-2">{trade.created_at.slice(0, 10)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-end space-x-3">
                    <button
                      onClick={() => setIsEditing(true)}
                      className="px-4 py-2 bg-yellow-600 rounded hover:bg-yellow-700"
                    >
                      Edit User
                    </button>
                    <button
                      onClick={closeModal}
                      className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-700"
                    >
                      Close
                    </button>
                  </div>
                </div>
              ) : (
                // Edit Mode
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
                      <input
                        type="email"
                        value={selectedUser.email}
                        disabled
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white disabled:opacity-50"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
                      <input
                        type="text"
                        value={editForm.username}
                        onChange={(e) => setEditForm(prev => ({ ...prev, username: e.target.value }))}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Role</label>
                      <select
                        value={editForm.role}
                        onChange={(e) => setEditForm(prev => ({ ...prev, role: e.target.value }))}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Subscription</label>
                      <select
                        value={editForm.subscription_tier}
                        onChange={(e) => setEditForm(prev => ({ ...prev, subscription_tier: e.target.value }))}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      >
                        <option value="">Free</option>
                        <option value="basic">Basic</option>
                        <option value="premium">Premium</option>
                        <option value="pro">Pro</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                      <select
                        value={editForm.is_active.toString()}
                        onChange={(e) => setEditForm(prev => ({ ...prev, is_active: e.target.value === 'true' }))}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      >
                        <option value="true">Active</option>
                        <option value="false">Inactive</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex justify-end space-x-3">
                    <button
                      onClick={handleCancel}
                      className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-700"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      className="px-4 py-2 bg-green-600 rounded hover:bg-green-700"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 