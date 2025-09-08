/**
 * Alice v2 API SDK
 * TypeScript SDK for Alice AI Assistant API
 */

// Re-export types from @alice/types
// Note: This creates a circular dependency, so we'll export specific types instead
export type { 
  ChatRequest, 
  ChatResponse, 
  ASREvent, 
  ASRWebSocketMessage, 
  VoiceSession 
} from '@alice/types';

// Export clients
export { BaseClient, BaseClientOptions, RequestOptions, AliceAPIError } from './clients/base-client';
export { OrchestratorClient, OrchestratorClientOptions } from './clients/orchestrator-client';
export { GuardianClient, GuardianClientOptions } from './clients/guardian-client';
export { AliceAPIClient, type AliceAPIConfig } from './clients/alice-api-client';

// Import client classes for convenience exports
import { OrchestratorClient } from './clients/orchestrator-client';
import { GuardianClient } from './clients/guardian-client';
import { AliceAPIClient } from './clients/alice-api-client';

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
  AliceAPIClient,
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