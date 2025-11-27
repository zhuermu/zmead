'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

type ConnectionState = 'connected' | 'connecting' | 'reconnecting' | 'disconnected';

interface WebSocketMessage {
  type: string;
  content?: string;
  data?: any;
  timestamp?: string;
}

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  heartbeatInterval?: number;
  heartbeatTimeout?: number;
  maxReconnectAttempts?: number;
  reconnectBackoff?: number[];
  maxQueueSize?: number;
}

const DEFAULT_OPTIONS: Required<UseWebSocketOptions> = {
  url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/chat',
  autoConnect: true,
  heartbeatInterval: 30000, // 30 seconds
  heartbeatTimeout: 60000, // 60 seconds
  maxReconnectAttempts: 3,
  reconnectBackoff: [1000, 2000, 4000], // 1s, 2s, 4s
  maxQueueSize: 10,
};

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastError, setLastError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const isManualCloseRef = useRef(false);

  // Send message
  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      // Queue message if disconnected
      if (messageQueueRef.current.length < opts.maxQueueSize) {
        messageQueueRef.current.push(message);
        console.log('Message queued (offline):', message.type);
        return false;
      } else {
        console.warn('Message queue full, dropping message:', message.type);
        return false;
      }
    }
  }, [opts.maxQueueSize]);

  // Send queued messages
  const sendQueuedMessages = useCallback(() => {
    if (messageQueueRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
      console.log(`Sending ${messageQueueRef.current.length} queued messages`);
      
      messageQueueRef.current.forEach((message) => {
        wsRef.current?.send(JSON.stringify(message));
      });
      
      messageQueueRef.current = [];
    }
  }, []);

  // Start heartbeat
  const startHeartbeat = useCallback(() => {
    // Clear existing intervals
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }

    // Send ping every 30 seconds
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
        
        // Set timeout for pong response
        heartbeatTimeoutRef.current = setTimeout(() => {
          console.warn('Heartbeat timeout - no pong received');
          wsRef.current?.close();
        }, opts.heartbeatTimeout);
      }
    }, opts.heartbeatInterval);
  }, [opts.heartbeatInterval, opts.heartbeatTimeout]);

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Reconnect with exponential backoff
  const reconnect = useCallback(() => {
    if (isManualCloseRef.current) {
      console.log('Manual close - not reconnecting');
      return;
    }

    if (reconnectAttemptRef.current >= opts.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      setConnectionState('disconnected');
      setLastError('连接已断开，请刷新页面');
      return;
    }

    const backoffDelay = opts.reconnectBackoff[reconnectAttemptRef.current] || 4000;
    console.log(`Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttemptRef.current + 1}/${opts.maxReconnectAttempts})`);
    
    setConnectionState('reconnecting');
    
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptRef.current++;
      connect();
    }, backoffDelay);
  }, [opts.maxReconnectAttempts, opts.reconnectBackoff]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    try {
      setConnectionState('connecting');
      setLastError(null);
      
      // Get auth token
      const token = localStorage.getItem('auth_token');
      const wsUrl = token ? `${opts.url}?token=${token}` : opts.url;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionState('connected');
        reconnectAttemptRef.current = 0;
        
        // Start heartbeat
        startHeartbeat();
        
        // Send queued messages
        sendQueuedMessages();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle pong response
          if (message.type === 'pong') {
            if (heartbeatTimeoutRef.current) {
              clearTimeout(heartbeatTimeoutRef.current);
              heartbeatTimeoutRef.current = null;
            }
            return;
          }
          
          // Handle other messages (will be processed by chat components)
          console.log('WebSocket message received:', message.type);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setLastError('连接错误');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        stopHeartbeat();
        
        if (!isManualCloseRef.current) {
          setConnectionState('disconnected');
          reconnect();
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionState('disconnected');
      setLastError('连接失败');
      reconnect();
    }
  }, [opts.url, startHeartbeat, stopHeartbeat, sendQueuedMessages, reconnect]);

  // Disconnect
  const disconnect = useCallback(() => {
    isManualCloseRef.current = true;
    
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    stopHeartbeat();
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionState('disconnected');
  }, [stopHeartbeat]);

  // Auto-connect on mount
  useEffect(() => {
    if (opts.autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [opts.autoConnect]);

  return {
    connectionState,
    lastError,
    sendMessage,
    connect,
    disconnect,
    isConnected: connectionState === 'connected',
  };
}
