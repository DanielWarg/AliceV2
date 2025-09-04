import type {
  APIResponse,
  ChatRequest,
  ChatResponse,
  NLURequest,
  NLUResponse,
  TTSRequest,
  TTSResponse,
  LLMStatus,
  HealthStatus,
  GuardianStatus,
} from '@alice/types';

export interface HTTPClientConfig {
  baseURL: string;
  guardianURL: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export class CircuitBreaker {
  private failures = 0;
  private lastFailureTime = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(
    private threshold = 5,
    private timeout = 60000, // 60s
    private resetTimeout = 30000, // 30s
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (Date.now() - this.lastFailureTime > this.resetTimeout) {
        this.state = 'half-open';
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess() {
    this.failures = 0;
    this.state = 'closed';
  }

  private onFailure() {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.failures >= this.threshold) {
      this.state = 'open';
    }
  }

  getState() {
    return {
      state: this.state,
      failures: this.failures,
      lastFailureTime: this.lastFailureTime,
    };
  }
}

export class HTTPClient {
  private circuitBreaker: CircuitBreaker;
  private requestId = 0;

  constructor(private config: HTTPClientConfig) {
    this.circuitBreaker = new CircuitBreaker();
  }

  private generateRequestId(): string {
    return `req_${++this.requestId}_${Date.now()}`;
  }

  private async fetchWithRetry<T>(url: string, options: RequestInit = {}): Promise<T> {
    const requestId = this.generateRequestId();

    const fetchOperation = async (): Promise<T> => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout || 10000);

      try {
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': requestId,
            ...options.headers,
          },
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        clearTimeout(timeoutId);
        throw error;
      }
    };

    return this.circuitBreaker.execute(fetchOperation);
  }

  // Chat & LLM APIs
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    return this.fetchWithRetry<ChatResponse>(`${this.config.baseURL}/api/chat`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getLLMStatus(): Promise<LLMStatus> {
    return this.fetchWithRetry<LLMStatus>(`${this.config.baseURL}/api/v1/llm/status`);
  }

  // Voice Pipeline APIs
  async classifyIntent(request: NLURequest): Promise<NLUResponse> {
    return this.fetchWithRetry<NLUResponse>(`${this.config.baseURL}/api/nlu/classify`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async generateTTS(request: TTSRequest): Promise<TTSResponse> {
    return this.fetchWithRetry<TTSResponse>(`${this.config.baseURL}/api/tts/`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Guardian System APIs
  async getGuardianStatus(): Promise<GuardianStatus> {
    return this.fetchWithRetry<GuardianStatus>(`${this.config.guardianURL}/health`);
  }

  // System Health APIs
  async getAliceHealth(): Promise<HealthStatus> {
    return this.fetchWithRetry<HealthStatus>(`${this.config.baseURL}/health`);
  }

  // File Operations
  async uploadFile(file: File): Promise<APIResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.fetchWithRetry<APIResponse>(`${this.config.baseURL}/api/upload`, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    });
  }

  // Utility methods
  getCircuitBreakerState() {
    return this.circuitBreaker.getState();
  }

  isHealthy(): boolean {
    return this.circuitBreaker.getState().state !== 'open';
  }
}
