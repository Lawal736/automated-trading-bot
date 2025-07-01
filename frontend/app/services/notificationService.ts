import { useAuth } from '../contexts/AuthContext';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  data?: any;
}

export interface TradeNotification extends Notification {
  data: {
    bot_id: string;
    bot_name: string;
    symbol: string;
    side: 'buy' | 'sell';
    quantity: number;
    price: number;
    pnl?: number;
  };
}

export interface SystemNotification extends Notification {
  data: {
    event_type: string;
    user_id?: string;
    details?: any;
  };
}

class NotificationService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Function[]> = new Map();
  private notifications: Notification[] = [];
  private _isConnected = false;

  constructor() {
    this.setupWebSocket();
  }

  private setupWebSocket() {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        console.warn('No auth token available for WebSocket connection');
        return;
      }

      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || '/api/v1/ws';
      this.ws = new WebSocket(`${wsUrl}?token=${token}`);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this._isConnected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this._isConnected = false;
        this.emit('disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this._isConnected = false;
      };
    } catch (error) {
      console.error('Failed to setup WebSocket:', error);
    }
  }

  private handleMessage(data: any) {
    switch (data.type) {
      case 'notification':
        this.addNotification(data.notification);
        break;
      case 'trade_update':
        this.emit('trade_update', data.trade);
        break;
      case 'bot_status':
        this.emit('bot_status', data.bot);
        break;
      case 'system_alert':
        this.emit('system_alert', data.alert);
        break;
      default:
        console.warn('Unknown message type:', data.type);
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      this.setupWebSocket();
    }, delay);
  }

  private addNotification(notification: Notification) {
    this.notifications.unshift(notification);
    
    // Keep only the last 100 notifications
    if (this.notifications.length > 100) {
      this.notifications = this.notifications.slice(0, 100);
    }

    this.emit('notification', notification);
    
    // Show browser notification if supported
    this.showBrowserNotification(notification);
  }

  private showBrowserNotification(notification: Notification) {
    if (!('Notification' in window)) {
      return;
    }

    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico',
        tag: notification.id,
      });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
          this.showBrowserNotification(notification);
        }
      });
    }
  }

  // Event listener management
  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  off(event: string, callback: Function) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  private emit(event: string, data?: any) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  // Public methods
  getNotifications(): Notification[] {
    return [...this.notifications];
  }

  getUnreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }

  markAsRead(notificationId: string) {
    const notification = this.notifications.find(n => n.id === notificationId);
    if (notification) {
      notification.read = true;
      this.emit('notification_updated', notification);
    }
  }

  markAllAsRead() {
    this.notifications.forEach(n => n.read = true);
    this.emit('notifications_updated');
  }

  clearNotifications() {
    this.notifications = [];
    this.emit('notifications_cleared');
  }

  isConnected(): boolean {
    return this._isConnected;
  }

  // Send message to server
  send(type: string, data: any) {
    if (this.ws && this._isConnected) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket not connected');
    }
  }

  // Subscribe to specific events
  subscribeToBot(botId: string) {
    this.send('subscribe_bot', { bot_id: botId });
  }

  unsubscribeFromBot(botId: string) {
    this.send('unsubscribe_bot', { bot_id: botId });
  }

  // Disconnect
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._isConnected = false;
  }
}

// Create singleton instance
export const notificationService = new NotificationService();

// React hook for notifications
export function useNotifications() {
  const { user } = useAuth();
  
  return {
    notifications: notificationService.getNotifications(),
    unreadCount: notificationService.getUnreadCount(),
    isConnected: notificationService.isConnected(),
    markAsRead: notificationService.markAsRead.bind(notificationService),
    markAllAsRead: notificationService.markAllAsRead.bind(notificationService),
    clearNotifications: notificationService.clearNotifications.bind(notificationService),
  };
} 
