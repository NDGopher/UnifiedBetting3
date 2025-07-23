import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketHook {
  lastMessage: MessageEvent | null;
  sendMessage: (message: string) => void;
  isConnected: boolean;
}

export const useWebSocket = (url: string): WebSocketHook => {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        // Enhanced reconnection with exponential backoff
        setTimeout(() => {
          console.log('Attempting WebSocket reconnection...');
          connect();
        }, 5000);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.current.onmessage = (event) => {
        setLastMessage(event);
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendMessage = useCallback((message: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  return { lastMessage, sendMessage, isConnected };
}; 