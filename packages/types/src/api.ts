/**
 * Alice v2 API Types
 * Shared TypeScript types and Zod schemas for API communication
 */

import { z } from 'zod';

// API Version
export const API_VERSION = '1' as const;

// Model Types
export enum ModelType {
  AUTO = 'auto',
  MICRO = 'micro',
  PLANNER = 'planner',
  DEEP = 'deep',
}

export enum GuardianState {
  NORMAL = 'NORMAL',
  BROWNOUT = 'BROWNOUT',
  DEGRADED = 'DEGRADED',
  EMERGENCY = 'EMERGENCY',
  LOCKDOWN = 'LOCKDOWN',
}

// Zod Schemas
export const BaseRequestSchema = z.object({
  v: z.literal(API_VERSION),
  session_id: z.string().min(1),
  timestamp: z.number().int().optional(),
});

export const BaseResponseSchema = z.object({
  v: z.literal(API_VERSION),
  session_id: z.string(),
  timestamp: z.number().int(),
  trace_id: z.string().optional(),
});

export const ChatRequestSchema = BaseRequestSchema.extend({
  message: z.string().min(1).max(10000),
  model: z.nativeEnum(ModelType).optional(),
  context: z.record(z.unknown()).optional(),
});

export const ChatResponseSchema = BaseResponseSchema.extend({
  response: z.string(),
  model_used: z.nativeEnum(ModelType),
  latency_ms: z.number().int(),
  metadata: z.record(z.unknown()).optional(),
});

export const IngestRequestSchema = BaseRequestSchema.extend({
  text: z.string().min(1).max(10000),
  lang: z.string().optional(),
  intent: z.string().optional(),
  context: z.record(z.unknown()).optional(),
});

export const IngestResponseSchema = BaseResponseSchema.extend({
  accepted: z.boolean(),
  model: z.nativeEnum(ModelType),
  priority: z.number().int().min(1).max(10),
  estimated_latency_ms: z.number().int(),
  reason: z.string().optional(),
});

export const APIErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
    trace_id: z.string().optional(),
    retry_after: z.number().int().optional(),
  }),
});

export const HealthResponseSchema = z.object({
  status: z.enum(['healthy', 'degraded', 'unhealthy']),
  service: z.string(),
  version: z.string(),
  timestamp: z.number().int(),
  dependencies: z.record(z.unknown()),
  metrics: z.record(z.unknown()).optional(),
});

// TypeScript Types (inferred from schemas)
export type BaseRequest = z.infer<typeof BaseRequestSchema>;
export type BaseResponse = z.infer<typeof BaseResponseSchema>;
export type ChatRequest = z.infer<typeof ChatRequestSchema>;
export type ChatResponse = z.infer<typeof ChatResponseSchema>;
export type IngestRequest = z.infer<typeof IngestRequestSchema>;
export type IngestResponse = z.infer<typeof IngestResponseSchema>;
export type APIError = z.infer<typeof APIErrorSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

// Guardian Types
export const GuardianHealthSchema = z.object({
  state: z.nativeEnum(GuardianState),
  available: z.boolean(),
  ram_pct: z.number().optional(),
  cpu_pct: z.number().optional(),
  uptime_s: z.number().optional(),
  brownout_level: z.string().optional(),
});

export type GuardianHealth = z.infer<typeof GuardianHealthSchema>;

// Utility type for HTTP responses
export type ApiResponse<T> = T | APIError;

// Helper functions for type guards
export function isApiError(response: unknown): response is APIError {
  return APIErrorSchema.safeParse(response).success;
}

export function isApiSuccess<T>(response: ApiResponse<T>): response is T {
  return !isApiError(response);
}