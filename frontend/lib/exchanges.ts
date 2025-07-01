import { backendApiClient } from './api';

export interface ExchangeConnection {
  id: number;
  exchange_name: string;
  api_key: string;
  is_testnet: boolean;
  created_at: string;
}

export interface NewExchangeConnection {
  exchange_name: string;
  api_key: string;
  api_secret: string;
  is_testnet: boolean;
  password?: string;
}

export const getExchangeConnections = async (): Promise<ExchangeConnection[]> => {
  try {
    const response = await backendApiClient.get('/exchanges');
    return response.data;
  } catch (error) {
    console.error("Failed to fetch exchange connections:", error);
    throw error;
  }
};

export const createExchangeConnection = async (
  payload: NewExchangeConnection
): Promise<ExchangeConnection> => {
  try {
    const response = await backendApiClient.post('/exchanges', payload);
    return response.data;
  } catch (error) {
    console.error("Failed to create exchange connection:", error);
    if (error.response) {
      throw new Error(error.response.data.detail || "Failed to create exchange connection. Please try again.");
    }
    throw new Error("Failed to create exchange connection. Please try again.");
  }
};

export async function getExchanges(): Promise<ExchangeConnection[]> {
  try {
    const response = await backendApiClient.get('/exchanges/');
    return response.data;
  } catch (error) {
    console.error("Failed to fetch exchanges:", error);
    throw error;
  }
}

export const getTickerPrice = async (symbol: string, exchangeName: string = 'binance') => {
  try {
    const response = await backendApiClient.get(`/exchanges/${exchangeName}/ticker?symbol=${symbol}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch ticker price:", error);
    return null;
  }
};

export interface TradeOrder {
    symbol: string;
    side: 'buy' | 'sell';
    order_type: 'market' | 'limit';
    trade_type: 'spot' | 'futures';
    amount: number;
    price?: number;
    stop_loss?: number;
    leverage?: number;
    enable_ema25_trailing?: boolean;
}

export async function executeTrade(exchangeName: string, order: TradeOrder) {
    const response = await backendApiClient.post(`/exchanges/${exchangeName}/trade`, order);
    return response.data;
}

export async function getTopTradingPairs(clearCache: boolean = false): Promise<string[]> {
    try {
        const response = await backendApiClient.get(`/exchanges/binance/top-pairs?clear_cache=${clearCache}`);
        return response.data;
    } catch (error) {
        console.error("Failed to fetch top trading pairs:", error);
        // Fallback to default pairs if API fails
        return [
            'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT',
            'BNB/USDT', 'XRP/USDT', 'SOL/USDT', 'MATIC/USDT', 'AVAX/USDT'
        ];
    }
}