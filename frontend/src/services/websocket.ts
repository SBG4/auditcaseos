/**
 * WebSocket service for real-time updates
 */

export type WebSocketMessageType =
  | 'connected'
  | 'presence'
  | 'case_created'
  | 'case_updated'
  | 'evidence_added'
  | 'evidence_deleted'
  | 'finding_added'
  | 'finding_updated'
  | 'timeline_added'
  | 'status_changed'
  | 'ping'
  | 'pong'
  | 'error';

export interface ViewerInfo {
  user_id: string;
  email: string;
  name: string;
  connected_at: string;
}

export interface WebSocketMessage {
  type: WebSocketMessageType;
  case_id?: string;
  data?: Record<string, unknown>;
  viewers?: ViewerInfo[];
  timestamp: string;
  error?: string;
  message?: string;
}

type MessageHandler = (message: WebSocketMessage) => void;

interface WebSocketConfig {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

const DEFAULT_CONFIG: Required<WebSocketConfig> = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  heartbeatInterval: 30000,
};

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private caseId: string | null = null;
  private reconnectAttempts = 0;
  private reconnectTimeout: number | null = null;
  private heartbeatInterval: number | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private config: Required<WebSocketConfig>;
  private isIntentionalClose = false;

  constructor(config: WebSocketConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Connect to WebSocket for a specific case
   */
  connect(caseId: string): void {
    if (this.ws && this.caseId === caseId && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected to case:', caseId);
      return;
    }

    // Close existing connection if connecting to different case
    if (this.ws) {
      this.disconnect();
    }

    this.caseId = caseId;
    this.isIntentionalClose = false;
    this.createConnection();
  }

  private createConnection(): void {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('No access token found, cannot connect WebSocket');
      return;
    }

    if (!this.caseId) {
      console.error('No case ID set, cannot connect WebSocket');
      return;
    }

    // Build WebSocket URL
    // In development, connect directly to API
    // In production (via nginx), use relative URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}`;
    const wsUrl = `${host}/api/v1/ws/cases/${this.caseId}?token=${encodeURIComponent(token)}`;

    console.log('Connecting WebSocket to:', wsUrl.replace(token, '***'));

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected to case:', this.caseId);
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.stopHeartbeat();

      if (!this.isIntentionalClose && event.code !== 4001) {
        // 4001 is auth failure - don't reconnect
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleMessage(message: WebSocketMessage): void {
    // Handle ping internally
    if (message.type === 'ping') {
      this.sendPong();
      return;
    }

    // Notify all handlers
    this.handlers.forEach((handler) => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in WebSocket message handler:', error);
      }
    });
  }

  private sendPong(): void {
    this.send({ type: 'pong' });
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = window.setInterval(() => {
      this.send({ type: 'heartbeat' });
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      window.clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    if (this.reconnectTimeout) {
      window.clearTimeout(this.reconnectTimeout);
    }

    const delay = this.config.reconnectInterval * Math.pow(1.5, this.reconnectAttempts);
    console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectAttempts++;
      this.createConnection();
    }, delay);
  }

  /**
   * Send a message through the WebSocket
   */
  send(data: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message');
      return;
    }

    try {
      this.ws.send(JSON.stringify(data));
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
    }
  }

  /**
   * Register a message handler
   */
  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.isIntentionalClose = true;
    this.stopHeartbeat();

    if (this.reconnectTimeout) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.caseId = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get current case ID
   */
  getCurrentCaseId(): string | null {
    return this.caseId;
  }
}

// Singleton instance
export const wsClient = new WebSocketClient();
