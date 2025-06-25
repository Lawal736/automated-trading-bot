"use client";

import { useState, useEffect } from 'react';
import { ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { getTopTradingPairs } from '../lib/exchanges';

interface TradingPairsSelectProps {
  selectedPairs: string[];
  onPairsChange: (pairs: string[]) => void;
  className?: string;
}

export default function TradingPairsSelect({ 
  selectedPairs, 
  onPairsChange, 
  className = "" 
}: TradingPairsSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [availablePairs, setAvailablePairs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPairs = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const pairs = await getTopTradingPairs();
        setAvailablePairs(pairs);
      } catch (err) {
        setError('Failed to load trading pairs');
        console.error('Error fetching trading pairs:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPairs();
  }, []);

  const handlePairToggle = (pair: string) => {
    if (selectedPairs.includes(pair)) {
      onPairsChange(selectedPairs.filter(p => p !== pair));
    } else {
      onPairsChange([...selectedPairs, pair]);
    }
  };

  const handleSelectAll = () => {
    onPairsChange(availablePairs);
  };

  const handleClearAll = () => {
    onPairsChange([]);
  };

  const removePair = (pair: string) => {
    onPairsChange(selectedPairs.filter(p => p !== pair));
  };

  return (
    <div className={`relative ${className}`}>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Trading Pairs
      </label>
      
      {/* Selected pairs display */}
      {selectedPairs.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {selectedPairs.map((pair) => (
            <span
              key={pair}
              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-600 text-white text-sm rounded-md"
            >
              {pair}
              <button
                type="button"
                onClick={() => removePair(pair)}
                className="hover:bg-blue-700 rounded-full p-0.5"
              >
                <XMarkIcon className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Dropdown button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-left text-white hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <span className={selectedPairs.length === 0 ? 'text-gray-400' : 'text-white'}>
          {selectedPairs.length === 0 
            ? 'Select trading pairs...' 
            : `${selectedPairs.length} pair${selectedPairs.length !== 1 ? 's' : ''} selected`
          }
        </span>
        <ChevronDownIcon className={`h-5 w-5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-600 rounded-md shadow-lg max-h-60 overflow-y-auto">
          {isLoading ? (
            <div className="px-3 py-2 text-gray-400">Loading pairs...</div>
          ) : error ? (
            <div className="px-3 py-2 text-red-400">{error}</div>
          ) : (
            <>
              {/* Action buttons */}
              <div className="flex gap-2 p-2 border-b border-gray-600">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={handleClearAll}
                  className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded"
                >
                  Clear All
                </button>
              </div>

              {/* Pairs list */}
              <div className="max-h-48 overflow-y-auto">
                {availablePairs.map((pair) => (
                  <label
                    key={pair}
                    className="flex items-center px-3 py-2 hover:bg-gray-700 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedPairs.includes(pair)}
                      onChange={() => handlePairToggle(pair)}
                      className="mr-3 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-white">{pair}</span>
                  </label>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
} 