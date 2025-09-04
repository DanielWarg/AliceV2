import { OrchestratorClient, type OrchestratorClientOptions } from './orchestrator-client';
import { WebSocketClient, type WebSocketClientConfig } from './websocket-client';
import type { ChatRequest, ChatResponse } from '@alice/types';

export interface AliceAPIConfig {
  baseURL: string;
  wsURL: string;
  guardianURL: string;
  timeout?: number;
  retries?: number;
}

export class AliceAPIClient {
  private orchestrator: OrchestratorClient;
  private websocket: WebSocketClient | null = null;
  private config: AliceAPIConfig;

  constructor(config: AliceAPIConfig) {
    this.config = config;

    const orchestratorOptions: OrchestratorClientOptions = {
      baseURL: config.baseURL,
      timeout: config.timeout || 10000,
      maxRetries: config.retries || 3,
    };

    this.orchestrator = new OrchestratorClient(orchestratorOptions);
  }

  async connectWebSocket(): Promise<void> {
    if (this.websocket) {
      return;
    }

    const wsConfig: WebSocketClientConfig = {
      url: this.config.wsURL,
      reconnectAttempts: 5,
      reconnectDelay: 1000,
      heartbeatInterval: 30000,
    };

    this.websocket = new WebSocketClient(wsConfig);
    await this.websocket.connect();
  }

  disconnect(): void {
    if (this.websocket) {
      this.websocket.disconnect();
      this.websocket = null;
    }
  }

  async sendChatMessage(message: ChatRequest): Promise<ChatResponse> {
    return await this.orchestrator.sendChatMessage(message);
  }

  async getHealth(): Promise<any> {
    return await this.orchestrator.getHealth();
  }

  async getGuardianHealth(): Promise<any> {
    const response = await fetch(`${this.config.guardianURL}/health`);
    return await response.json();
  }

  isConnected(): boolean {
    return this.websocket?.isConnected() || false;
  }

  async isHealthy(): Promise<boolean> {
    try {
      await this.orchestrator.getHealth();
      return true;
    } catch {
      return false;
    }
  }
}
