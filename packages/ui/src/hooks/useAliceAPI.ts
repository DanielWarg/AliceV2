import { useState, useEffect, useCallback } from 'react';
import { AliceAPIClient, type AliceAPIConfig } from '@alice/api';
import type { ChatRequest } from '@alice/types';

interface UseAliceAPIOptions {
  config: AliceAPIConfig;
  autoConnect?: boolean;
}

interface AliceAPIHookReturn {
  client: AliceAPIClient | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendMessage: (message: string) => Promise<any>;
}

export function useAliceAPI({
  config,
  autoConnect = true,
}: UseAliceAPIOptions): AliceAPIHookReturn {
  const [client, setClient] = useState<AliceAPIClient | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize client
  useEffect(() => {
    const apiClient = new AliceAPIClient(config);
    setClient(apiClient);

    return () => {
      apiClient.disconnect();
    };
  }, [config]);

  const connect = useCallback(async () => {
    if (!client || isConnecting || isConnected) return;

    setIsConnecting(true);
    setError(null);

    try {
      await client.connectWebSocket();
      setIsConnected(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Connection failed';
      setError(errorMessage);
      console.error('Alice API connection failed:', err);
    } finally {
      setIsConnecting(false);
    }
  }, [client, isConnecting, isConnected]);

  const disconnect = useCallback(() => {
    if (!client) return;

    client.disconnect();
    setIsConnected(false);
    setError(null);
  }, [client]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!client) {
        throw new Error('Client not initialized');
      }

      if (!isConnected) {
        throw new Error('Not connected to Alice API');
      }

      const chatRequest: ChatRequest = {
        v: '1',
        session_id: 'web-session',
        message: message,
        timestamp: Date.now(),
      };

      return await client.sendChatMessage(chatRequest);
    },
    [client, isConnected],
  );

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && client && !isConnected && !isConnecting) {
      connect();
    }
  }, [autoConnect, client, isConnected, isConnecting, connect]);

  return {
    client,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage,
  };
}
