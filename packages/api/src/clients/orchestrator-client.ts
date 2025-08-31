/**
 * Orchestrator API Client
 * Main client for Alice v2 chat and orchestration services
 */

import {
  ChatRequest,
  ChatResponse,
  IngestRequest,
  IngestResponse,
  HealthResponse,
  ChatRequestSchema,
  ChatResponseSchema,
  IngestRequestSchema,
  IngestResponseSchema,
  HealthResponseSchema,
  ModelType,
  API_VERSION,
} from '@alice/types';
import { BaseClient, BaseClientOptions, RequestOptions } from './base-client';

export interface OrchestratorClientOptions extends BaseClientOptions {
  defaultSessionId?: string;
}

export class OrchestratorClient extends BaseClient {
  private readonly defaultSessionId?: string;

  constructor(options: OrchestratorClientOptions) {
    super({
      ...options,
      baseURL: options.baseURL || 'http://localhost:8000',
    });
    
    this.defaultSessionId = options.defaultSessionId;
  }

  /**
   * Send chat message and get AI response
   */
  async chat(
    request: Omit<ChatRequest, 'v'> | Omit<ChatRequest, 'v' | 'session_id'>,
    options?: RequestOptions
  ): Promise<ChatResponse> {
    // Add version and default session ID if needed
    const fullRequest: ChatRequest = {
      v: API_VERSION,
      session_id: this.getSessionId(request),
      timestamp: Date.now(),
      ...request,
    };

    // Validate request
    const validatedRequest = ChatRequestSchema.parse(fullRequest);

    return this.post(
      '/api/chat',
      validatedRequest,
      ChatResponseSchema,
      options
    );
  }

  /**
   * Send text for orchestrator routing decision
   */
  async ingest(
    request: Omit<IngestRequest, 'v'> | Omit<IngestRequest, 'v' | 'session_id'>,
    options?: RequestOptions
  ): Promise<IngestResponse> {
    // Add version and default session ID if needed
    const fullRequest: IngestRequest = {
      v: API_VERSION,
      session_id: this.getSessionId(request),
      timestamp: Date.now(),
      ...request,
    };

    // Validate request
    const validatedRequest = IngestRequestSchema.parse(fullRequest);

    return this.post(
      '/api/orchestrator/ingest',
      validatedRequest,
      IngestResponseSchema,
      options
    );
  }

  /**
   * Get service health status
   */
  async health(options?: RequestOptions): Promise<HealthResponse> {
    return this.get('/health', HealthResponseSchema, options);
  }

  /**
   * Get orchestrator-specific health status
   */
  async orchestratorHealth(options?: RequestOptions): Promise<any> {
    return this.get('/api/orchestrator/health', undefined, options);
  }

  /**
   * Get chat service health status
   */
  async chatHealth(options?: RequestOptions): Promise<any> {
    return this.get('/api/chat/health', undefined, options);
  }

  /**
   * Convenience method for simple text chat
   */
  async sendMessage(
    message: string,
    sessionId?: string,
    model?: ModelType,
    options?: RequestOptions
  ): Promise<string> {
    const response = await this.chat(
      {
        message,
        session_id: sessionId || this.defaultSessionId || 'default',
        model,
      },
      options
    );

    return response.response;
  }

  /**
   * Convenience method to check if request would be accepted
   */
  async checkRouting(
    text: string,
    sessionId?: string,
    options?: RequestOptions
  ): Promise<{
    accepted: boolean;
    model: ModelType;
    estimatedLatency: number;
    reason?: string;
  }> {
    const response = await this.ingest(
      {
        text,
        session_id: sessionId || this.defaultSessionId || 'default',
      },
      options
    );

    return {
      accepted: response.accepted,
      model: response.model,
      estimatedLatency: response.estimated_latency_ms,
      reason: response.reason,
    };
  }

  /**
   * Get session ID from request or use default
   */
  private getSessionId(request: any): string {
    if ('session_id' in request && request.session_id) {
      return request.session_id;
    }
    
    if (this.defaultSessionId) {
      return this.defaultSessionId;
    }
    
    throw new Error('No session_id provided and no default session ID configured');
  }

  /**
   * Generate a new session ID
   */
  static generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}