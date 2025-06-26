"use client";

import { useState, useEffect } from 'react';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { getExchangeConnections, ExchangeConnection } from '../../../lib/exchanges';
import AddConnectionModal from '../../../components/AddConnectionModal';

export default function ExchangesPage() {
  const [connections, setConnections] = useState<ExchangeConnection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchConnections = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        throw new Error("Authentication token not found. Please log in again.");
      }
      const data = await getExchangeConnections();
      setConnections(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to fetch exchange connections.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConnections();
  }, []);

  const handleConnectionAdded = () => {
    fetchConnections(); // Re-fetch connections after one is added
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-bold leading-6 text-white">Exchange Connections</h1>
          <p className="mt-2 text-sm text-gray-400">
            Manage your API key connections to various exchanges.
          </p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            <PlusIcon className="-ml-0.5 mr-1.5 h-5 w-5" />
            Add Connection
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-red-900/50 p-4">
          <div className="flex">
            <div className="ml-3">
              <p className="text-sm font-medium text-red-300">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Connection List */}
      <div className="mt-8 flow-root">
        <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
             <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
                {isLoading ? (
                  <div className="flex justify-center items-center p-8">
                    <p className="text-gray-400">Loading connections...</p>
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-gray-700">
                    <thead className="bg-gray-800">
                      <tr>
                        <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-white sm:pl-6">Exchange</th>
                        <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-white">Environment</th>
                        <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-white">Connected On</th>
                        <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                          <span className="sr-only">Delete</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800 bg-gray-900">
                      {connections.length > 0 ? (
                        connections.map((conn) => (
                          <tr key={conn.id}>
                            <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-white sm:pl-6 capitalize">{conn.exchange_name}</td>
                            <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-300">
                              {conn.is_testnet ? (
                                <span className="inline-flex items-center rounded-md bg-yellow-900/50 px-2 py-1 text-xs font-medium text-yellow-300 ring-1 ring-inset ring-yellow-400/20">
                                  Testnet
                                </span>
                              ) : (
                                <span className="inline-flex items-center rounded-md bg-green-900/50 px-2 py-1 text-xs font-medium text-green-300 ring-1 ring-inset ring-green-400/20">
                                  Mainnet
                                </span>
                              )}
                            </td>
                            <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-300">{new Date(conn.created_at).toLocaleDateString()}</td>
                            <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                              <button className="text-red-500 hover:text-red-400">
                                <TrashIcon className="h-5 w-5" />
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="text-center py-5 text-gray-400">
                            No exchange connections found.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                )}
            </div>
          </div>
        </div>
      </div>
      
      <AddConnectionModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConnectionAdded={handleConnectionAdded}
      />
      
    </div>
  );
} 