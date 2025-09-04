/**
 * Base API Client
 * Foundation for all Alice v2 API communication
 */

import { z } from 'zod';
import { APIError, APIErrorSchema, isApiError, API_VERSION } from '@alice/types';
import { withRetry, CircuitBreaker, isRetriableHttpError, getRetryDelay } from '../utils/retry';

export interface BaseClientOptions {
  baseURL: string;
  timeout?: number;
  maxRetries?: number;
  circuitBreaker?: boolean;
  headers?: Record<string, string>;
}

export interface RequestOptions {
  timeout?: number;
  retries?: number;
  skipValidation?: boolean;
}

export class AliceAPIError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: any,
    public readonly traceId?: string,
    public readonly retryAfter?: number,
  ) {
    super(message);
    this.name = 'AliceAPIError';
  }

  static fromAPIError(error: APIError): AliceAPIError {
    const { code, message, details, trace_id, retry_after } = error.error;
    return new AliceAPIError(code, message, details, trace_id, retry_after);
  }
}

export class BaseClient {
  private readonly baseURL: string;
  private readonly timeout: number;
  private readonly maxRetries: number;
  private readonly headers: Record<string, string>;
  private readonly circuitBreaker?: CircuitBreaker;

  constructor(options: BaseClientOptions) {
    this.baseURL = options.baseURL.replace(/\/$/, ''); // Remove trailing slash
    this.timeout = options.timeout || 10000; // 10s default
    this.maxRetries = options.maxRetries || 3;
    this.headers = {
      'Content-Type': 'application/json',
      'User-Agent': 'Alice-SDK/1.0.0',
      ...options.headers,
    };

    if (options.circuitBreaker !== false) {
      this.circuitBreaker = new CircuitBreaker({
        failureThreshold: 5,
        recoveryTimeout: 30000,
        monitoringWindow: 60000,
      });
    }
  }

  /**
   * Make HTTP request with retry logic and circuit breaker
   */
  protected async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    path: string,
    options: RequestOptions = {},
  ): Promise<Response> {
    const url = `${this.baseURL}${path}`;
    const timeout = options.timeout || this.timeout;
    const maxRetries = options.retries !== undefined ? options.retries : this.maxRetries;

    const operation = async (): Promise<Response> => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(url, {
          method,
          headers: this.headers,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        return response;
      } catch (error) {
        clearTimeout(timeoutId);

        if (controller.signal.aborted) {
          const timeoutError = new Error(`Request timeout after ${timeout}ms`);
          timeoutError.name = 'TimeoutError';
          throw timeoutError;
        }

        throw error;
      }
    };

    // Use circuit breaker if available
    const executeRequest = this.circuitBreaker
      ? () => this.circuitBreaker!.execute(operation)
      : operation;

    // Apply retry logic
    return withRetry(executeRequest, {
      maxAttempts: maxRetries + 1,
      retryCondition: error => {
        // Add custom retry delay for 429 responses
        if (error.status === 429) {
          const retryDelay = getRetryDelay(error.headers);
          if (retryDelay > 0) {
            return true;
          }
        }
        return isRetriableHttpError(error);
      },
    });
  }

  /**
   * Make POST request with JSON body
   */
  protected async post<TRequest, TResponse>(
    path: string,
    body: TRequest,
    responseSchema?: z.ZodSchema<TResponse>,
    options: RequestOptions = {},
  ): Promise<TResponse> {
    const url = `${this.baseURL}${path}`;
    const timeout = options.timeout || this.timeout;
    const maxRetries = options.retries !== undefined ? options.retries : this.maxRetries;

    const operation = async (): Promise<Response> => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        return response;
      } catch (error) {
        clearTimeout(timeoutId);

        if (controller.signal.aborted) {
          const timeoutError = new Error(`Request timeout after ${timeout}ms`);
          timeoutError.name = 'TimeoutError';
          throw timeoutError;
        }

        throw error;
      }
    };

    // Use circuit breaker if available
    const executeRequest = this.circuitBreaker
      ? () => this.circuitBreaker!.execute(operation)
      : operation;

    // Apply retry logic
    const response = await withRetry(executeRequest, {
      maxAttempts: maxRetries + 1,
      retryCondition: isRetriableHttpError,
    });

    return this.handleResponse<TResponse>(response, responseSchema, options);
  }

  /**
   * Make GET request
   */
  protected async get<TResponse>(
    path: string,
    responseSchema?: z.ZodSchema<TResponse>,
    options: RequestOptions = {},
  ): Promise<TResponse> {
    const response = await this.request<TResponse>('GET', path, options);
    return this.handleResponse<TResponse>(response, responseSchema, options);
  }

  /**
   * Handle HTTP response with error checking and validation
   */
  private async handleResponse<T>(
    response: Response,
    schema?: z.ZodSchema<T>,
    options: RequestOptions = {},
  ): Promise<T> {
    // Parse response body
    let data: any;
    try {
      data = await response.json();
    } catch (error) {
      throw new Error(`Failed to parse JSON response: ${error}`);
    }

    // Check for API errors
    if (!response.ok) {
      // Try to parse as API error
      if (isApiError(data)) {
        throw AliceAPIError.fromAPIError(data);
      }

      // Generic HTTP error
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // Validate response if schema provided and validation not skipped
    if (schema && !options.skipValidation) {
      try {
        return schema.parse(data);
      } catch (error) {
        if (error instanceof z.ZodError) {
          throw new Error(`Response validation failed: ${error.message}`);
        }
        throw error;
      }
    }

    return data as T;
  }

  /**
   * Get circuit breaker status
   */
  public getCircuitBreakerStatus() {
    if (!this.circuitBreaker) return null;

    return {
      state: this.circuitBreaker.getState(),
      failures: this.circuitBreaker.getFailureCount(),
    };
  }

  /**
   * Reset circuit breaker
   */
  public resetCircuitBreaker() {
    if (this.circuitBreaker) {
      this.circuitBreaker.reset();
    }
  }
}
