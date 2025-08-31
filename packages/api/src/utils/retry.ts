/**
 * Retry Logic and Circuit Breaker
 * Handles robust API communication with automatic retries
 */

export interface RetryOptions {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  backoffFactor: number;
  retryCondition?: (error: any) => boolean;
}

export interface CircuitBreakerOptions {
  failureThreshold: number;
  recoveryTimeout: number;
  monitoringWindow: number;
}

export enum CircuitBreakerState {
  CLOSED = 'closed',
  OPEN = 'open', 
  HALF_OPEN = 'half-open',
}

export class RetryError extends Error {
  constructor(
    public readonly attempts: number,
    public readonly lastError: Error,
    message?: string
  ) {
    super(message || `Failed after ${attempts} attempts: ${lastError.message}`);
    this.name = 'RetryError';
  }
}

export class CircuitBreakerError extends Error {
  constructor(
    public readonly state: CircuitBreakerState,
    message?: string
  ) {
    super(message || `Circuit breaker is ${state}`);
    this.name = 'CircuitBreakerError';
  }
}

/**
 * Exponential backoff retry logic
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<T> {
  const config: RetryOptions = {
    maxAttempts: 3,
    baseDelay: 100,
    maxDelay: 5000,
    backoffFactor: 2,
    retryCondition: (error) => {
      // Retry on network errors, timeouts, and 5xx status codes
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        return true;
      }
      if (error.name === 'TimeoutError') {
        return true;
      }
      if (error.status && error.status >= 500) {
        return true;
      }
      // Don't retry on 4xx client errors (except 429 rate limiting)
      if (error.status && error.status >= 400 && error.status < 500) {
        return error.status === 429;
      }
      return true;
    },
    ...options,
  };

  let lastError: Error;

  for (let attempt = 1; attempt <= config.maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      // Don't retry if condition says no
      if (!config.retryCondition!(lastError)) {
        throw lastError;
      }
      
      // Don't delay after last attempt
      if (attempt === config.maxAttempts) {
        break;
      }

      // Calculate delay with exponential backoff + jitter
      const delay = Math.min(
        config.baseDelay * Math.pow(config.backoffFactor, attempt - 1),
        config.maxDelay
      );
      const jitter = delay * 0.1 * Math.random();
      
      await new Promise(resolve => setTimeout(resolve, delay + jitter));
    }
  }

  throw new RetryError(config.maxAttempts, lastError!);
}

/**
 * Circuit Breaker Pattern Implementation
 */
export class CircuitBreaker {
  private state = CircuitBreakerState.CLOSED;
  private failures = 0;
  private lastFailure: number = 0;
  private successCount = 0;

  constructor(private readonly options: CircuitBreakerOptions) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === CircuitBreakerState.OPEN) {
      if (Date.now() - this.lastFailure < this.options.recoveryTimeout) {
        throw new CircuitBreakerError(this.state, 'Circuit breaker is open');
      }
      // Try to recover
      this.state = CircuitBreakerState.HALF_OPEN;
      this.successCount = 0;
    }

    try {
      const result = await operation();
      
      // Success - reset failure count
      this.failures = 0;
      
      if (this.state === CircuitBreakerState.HALF_OPEN) {
        this.successCount++;
        // Need multiple successes to fully close circuit
        if (this.successCount >= 3) {
          this.state = CircuitBreakerState.CLOSED;
        }
      }
      
      return result;
    } catch (error) {
      this.failures++;
      this.lastFailure = Date.now();
      
      // Open circuit if failure threshold exceeded
      if (this.failures >= this.options.failureThreshold) {
        this.state = CircuitBreakerState.OPEN;
      }
      
      throw error;
    }
  }

  getState(): CircuitBreakerState {
    return this.state;
  }

  getFailureCount(): number {
    return this.failures;
  }

  reset(): void {
    this.state = CircuitBreakerState.CLOSED;
    this.failures = 0;
    this.successCount = 0;
  }
}

/**
 * HTTP-specific error checking
 */
export function isRetriableHttpError(error: any): boolean {
  // Network connectivity errors
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    return true;
  }
  
  // Timeout errors
  if (error.name === 'TimeoutError') {
    return true;
  }
  
  // HTTP status codes
  if (error.status) {
    // 5xx server errors are retriable
    if (error.status >= 500) {
      return true;
    }
    
    // 429 rate limiting is retriable
    if (error.status === 429) {
      return true;
    }
    
    // 408 request timeout is retriable
    if (error.status === 408) {
      return true;
    }
  }
  
  return false;
}

/**
 * Extract retry delay from HTTP headers
 */
export function getRetryDelay(headers?: Headers): number {
  if (!headers) return 0;
  
  // Check Retry-After header
  const retryAfter = headers.get('retry-after');
  if (retryAfter) {
    const delay = parseInt(retryAfter, 10);
    if (!isNaN(delay)) {
      return delay * 1000; // Convert to milliseconds
    }
  }
  
  return 0;
}