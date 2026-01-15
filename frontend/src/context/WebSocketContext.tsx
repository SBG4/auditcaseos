import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { wsClient, WebSocketMessage, ViewerInfo } from '../services/websocket';

interface WebSocketContextType {
  isConnected: boolean;
  viewers: ViewerInfo[];
  lastMessage: WebSocketMessage | null;
  connect: (caseId: string) => void;
  disconnect: () => void;
  send: (data: Record<string, unknown>) => void;
  subscribe: (handler: (message: WebSocketMessage) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false);
  const [viewers, setViewers] = useState<ViewerInfo[]>([]);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    // Set up internal message handler for connection state and presence
    const unsubscribe = wsClient.onMessage((message) => {
      setLastMessage(message);

      switch (message.type) {
        case 'connected':
          setIsConnected(true);
          if (message.viewers) {
            setViewers(message.viewers);
          }
          break;
        case 'presence':
          if (message.viewers) {
            setViewers(message.viewers);
          }
          break;
        case 'error':
          console.error('WebSocket error:', message.error);
          break;
      }
    });

    // Check connection state periodically
    const interval = setInterval(() => {
      setIsConnected(wsClient.isConnected());
    }, 1000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, []);

  const connect = useCallback((caseId: string) => {
    wsClient.connect(caseId);
  }, []);

  const disconnect = useCallback(() => {
    wsClient.disconnect();
    setIsConnected(false);
    setViewers([]);
    setLastMessage(null);
  }, []);

  const send = useCallback((data: Record<string, unknown>) => {
    wsClient.send(data);
  }, []);

  const subscribe = useCallback((handler: (message: WebSocketMessage) => void) => {
    return wsClient.onMessage(handler);
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        viewers,
        lastMessage,
        connect,
        disconnect,
        send,
        subscribe,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
