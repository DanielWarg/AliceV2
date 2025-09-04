import { useState, useEffect, useCallback } from 'react';
import type { GuardianStatus } from '@alice/types';

interface UseGuardianOptions {
  pollInterval?: number;
  apiUrl?: string;
  onStateChange?: (status: GuardianStatus) => void;
}

interface GuardianHookReturn {
  status: GuardianStatus | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  isDegraded: boolean;
  isEmergency: boolean;
  shouldShowBanner: boolean;
}

export function useGuardian({
  pollInterval = 5000,
  apiUrl = '/api/guardian/status',
  onStateChange,
}: UseGuardianOptions = {}): GuardianHookReturn {
  const [status, setStatus] = useState<GuardianStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(0);

  const fetchStatus = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(apiUrl);

      if (!response.ok) {
        throw new Error(`Guardian API error: ${response.status}`);
      }

      const newStatus: GuardianStatus = await response.json();

      // Check for state changes
      if (status && status.status !== newStatus.status) {
        onStateChange?.(newStatus);
      }

      setStatus(newStatus);
      setLastUpdate(Date.now());
      setIsLoading(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setIsLoading(false);
      console.error('Guardian status fetch failed:', err);
    }
  }, [apiUrl, status, onStateChange]);

  // Initial fetch and polling
  useEffect(() => {
    fetchStatus();

    if (pollInterval > 0) {
      const interval = setInterval(fetchStatus, pollInterval);
      return () => clearInterval(interval);
    }
  }, [fetchStatus, pollInterval]);

  // Derived states
  const isDegraded = status ? ['degraded', 'emergency', 'lockdown'].includes(status.status) : false;
  const isEmergency = status ? ['emergency', 'lockdown'].includes(status.status) : false;
  const shouldShowBanner = status ? status.status !== 'normal' : false;

  return {
    status,
    isLoading,
    error,
    refresh: fetchStatus,
    isDegraded,
    isEmergency,
    shouldShowBanner,
  };
}
