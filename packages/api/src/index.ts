/**
 * Alice v2 API SDK
 * TypeScript SDK for Alice AI Assistant API
 */

// Re-export types from @alice/types
export * from '@alice/types';

// Export clients
export { BaseClient, BaseClientOptions, RequestOptions, AliceAPIError } from './clients/base-client';
export { OrchestratorClient, OrchestratorClientOptions } from './clients/orchestrator-client';
export { GuardianClient, GuardianClientOptions } from './clients/guardian-client';

// Export utilities
export {
  withRetry,
  CircuitBreaker,
  RetryError,
  CircuitBreakerError,
  CircuitBreakerState,
  isRetriableHttpError,
  getRetryDelay,
  type RetryOptions,
  type CircuitBreakerOptions,
} from './utils/retry';

// Convenience exports for common use cases
export const AliceSDK = {
  OrchestratorClient,
  GuardianClient,
};

// Package metadata
export const SDK_VERSION = '1.0.0';
export const SUPPORTED_API_VERSION = '1';

/**
 * Create pre-configured Alice SDK clients
 */
export function createAliceClients(options: {
  orchestratorURL?: string;
  guardianURL?: string;
  defaultSessionId?: string;
  timeout?: number;
  maxRetries?: number;
}) {
  const orchestrator = new OrchestratorClient({
    baseURL: options.orchestratorURL || 'http://localhost:8000',
    defaultSessionId: options.defaultSessionId,
    timeout: options.timeout,
    maxRetries: options.maxRetries,
  });

  const guardian = new GuardianClient({
    baseURL: options.guardianURL || 'http://localhost:8787',
    timeout: options.timeout || 1000, // Faster for Guardian
  });

  return {
    orchestrator,
    guardian,
  };
}