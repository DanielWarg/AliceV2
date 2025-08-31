/**
 * Guardian API Client
 * Client for Alice v2 Guardian safety system monitoring
 */

import {
  GuardianHealth,
  GuardianHealthSchema,
  GuardianState,
} from '@alice/types';
import { BaseClient, BaseClientOptions, RequestOptions } from './base-client';

export interface GuardianClientOptions extends BaseClientOptions {
  pollInterval?: number;
}

export class GuardianClient extends BaseClient {
  private readonly pollInterval: number;
  private healthCache?: GuardianHealth;
  private lastHealthCheck: number = 0;
  private pollingTimer?: NodeJS.Timeout;

  constructor(options: GuardianClientOptions = {}) {
    super({
      ...options,
      baseURL: options.baseURL || 'http://localhost:8787',
      timeout: options.timeout || 1000, // Faster timeout for Guardian
    });
    
    this.pollInterval = options.pollInterval || 5000; // 5s default
  }

  /**
   * Get Guardian health status
   */
  async getHealth(useCache: boolean = true, options?: RequestOptions): Promise<GuardianHealth> {
    const now = Date.now();
    
    // Return cached result if recent
    if (useCache && this.healthCache && (now - this.lastHealthCheck) < 1000) {
      return this.healthCache;
    }

    try {
      const health = await this.get(
        '/guardian/health',
        GuardianHealthSchema,
        options
      );
      
      this.healthCache = health;
      this.lastHealthCheck = now;
      
      return health;
    } catch (error) {
      // Return degraded status on error
      const degradedHealth: GuardianHealth = {
        state: GuardianState.EMERGENCY,
        available: false,
      };
      
      this.healthCache = degradedHealth;
      this.lastHealthCheck = now;
      
      return degradedHealth;
    }
  }

  /**
   * Check if system is in safe state for requests
   */
  async isSafe(options?: RequestOptions): Promise<boolean> {
    try {
      const health = await this.getHealth(true, options);
      return health.available && 
             health.state !== GuardianState.EMERGENCY && 
             health.state !== GuardianState.LOCKDOWN;
    } catch {
      return false; // Fail-safe
    }
  }

  /**
   * Get recommended retry delay based on Guardian state
   */
  async getRetryDelay(options?: RequestOptions): Promise<number> {
    try {
      const health = await this.getHealth(true, options);
      
      const delayMap: Record<GuardianState, number> = {
        [GuardianState.NORMAL]: 0,
        [GuardianState.BROWNOUT]: 1000,   // 1s
        [GuardianState.DEGRADED]: 5000,   // 5s
        [GuardianState.EMERGENCY]: 30000, // 30s
        [GuardianState.LOCKDOWN]: 60000,  // 60s
      };
      
      return delayMap[health.state] || 5000;
    } catch {
      return 10000; // 10s default on error
    }
  }

  /**
   * Get system resource usage
   */
  async getResourceUsage(options?: RequestOptions): Promise<{
    ramPercent?: number;
    cpuPercent?: number;
    uptime?: number;
  }> {
    try {
      const health = await this.getHealth(false, options);
      return {
        ramPercent: health.ram_pct,
        cpuPercent: health.cpu_pct,
        uptime: health.uptime_s,
      };
    } catch {
      return {};
    }
  }

  /**
   * Start polling Guardian health in background
   */
  startPolling(): void {
    if (this.pollingTimer) {
      return; // Already polling
    }

    this.pollingTimer = setInterval(() => {
      this.getHealth(false).catch(() => {
        // Silent fail for background polling
      });
    }, this.pollInterval);
  }

  /**
   * Stop background health polling
   */
  stopPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = undefined;
    }
  }

  /**
   * Wait until system is safe for requests
   */
  async waitUntilSafe(
    maxWaitTime: number = 30000,
    checkInterval: number = 1000
  ): Promise<boolean> {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      const isSafe = await this.isSafe();
      if (isSafe) {
        return true;
      }

      await new Promise(resolve => setTimeout(resolve, checkInterval));
    }

    return false; // Timeout
  }

  /**
   * Get human-readable status message
   */
  async getStatusMessage(options?: RequestOptions): Promise<string> {
    try {
      const health = await this.getHealth(true, options);
      
      const messages: Record<GuardianState, string> = {
        [GuardianState.NORMAL]: 'System is operating normally',
        [GuardianState.BROWNOUT]: 'System is under moderate load, some features may be limited',
        [GuardianState.DEGRADED]: 'System is experiencing high load, reduced functionality',
        [GuardianState.EMERGENCY]: 'System is overloaded, most functions disabled',
        [GuardianState.LOCKDOWN]: 'System is in lockdown mode, all functions disabled',
      };
      
      return messages[health.state] || 'System status unknown';
    } catch {
      return 'Unable to determine system status';
    }
  }
}