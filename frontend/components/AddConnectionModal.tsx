"use client";

import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { NewExchangeConnection, createExchangeConnection } from '../lib/exchanges';

interface AddConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectionAdded: () => void;
}

export default function AddConnectionModal({ isOpen, onClose, onConnectionAdded }: AddConnectionModalProps) {
  const [exchange, setExchange] = useState('binance');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [password, setPassword] = useState('');
  const [isTestnet, setIsTestnet] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const payload: NewExchangeConnection = {
      exchange_name: exchange,
      api_key: apiKey,
      api_secret: apiSecret,
      is_testnet: isTestnet,
    };

    if (exchange === 'kucoin' || exchange === 'gateio') {
      payload.password = password;
    }

    try {
      await createExchangeConnection(payload);
      onConnectionAdded();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create connection.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-gray-800 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                <form onSubmit={handleSubmit}>
                  <div className="bg-gray-800 px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                    <div className="sm:flex sm:items-start">
                      <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                        <Dialog.Title as="h3" className="text-base font-semibold leading-6 text-white">
                          Add New Exchange Connection
                        </Dialog.Title>
                        <div className="mt-4 space-y-4">
                          <div>
                            <label htmlFor="exchange" className="block text-sm font-medium text-gray-300">Exchange</label>
                            <select id="exchange" value={exchange} onChange={(e) => setExchange(e.target.value)} className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm">
                              <option value="binance">Binance</option>
                              <option value="kucoin">KuCoin</option>
                              <option value="gateio">Gate.io</option>
                            </select>
                          </div>
                          <div>
                            <label htmlFor="apiKey" className="block text-sm font-medium text-gray-300">API Key</label>
                            <input type="text" id="apiKey" value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm" required />
                          </div>
                          <div>
                            <label htmlFor="apiSecret" className="block text-sm font-medium text-gray-300">API Secret</label>
                            <input type="password" id="apiSecret" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm" required />
                          </div>
                           {(exchange === 'kucoin' || exchange === 'gateio') && (
                            <div>
                                <label htmlFor="password">{exchange === 'kucoin' ? 'Passphrase' : 'Password'}</label>
                                <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm" required />
                            </div>
                           )}
                          <div className="flex items-center">
                            <input id="isTestnet" type="checkbox" checked={isTestnet} onChange={(e) => setIsTestnet(e.target.checked)} className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500" />
                            <label htmlFor="isTestnet" className="ml-2 block text-sm text-gray-300">Use Testnet</label>
                          </div>
                          {error && <p className="text-sm text-red-400">{error}</p>}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gray-900 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                    <button type="submit" disabled={isLoading} className="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 sm:ml-3 sm:w-auto disabled:opacity-50">
                      {isLoading ? 'Connecting...' : 'Connect'}
                    </button>
                    <button type="button" onClick={onClose} className="mt-3 inline-flex w-full justify-center rounded-md bg-gray-700 px-3 py-2 text-sm font-semibold text-white shadow-sm ring-1 ring-inset ring-gray-600 hover:bg-gray-600 sm:mt-0 sm:w-auto">
                      Cancel
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
} 