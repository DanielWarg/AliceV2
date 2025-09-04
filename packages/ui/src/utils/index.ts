import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Alice-specific utilities
export const formatLatency = (ms: number): string => {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

export const clampPercent = (value: number): number => {
  return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
};

export const safeUUID = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
};

// Guardian status helpers
export const getGuardianStatusColor = (status: string): string => {
  switch (status) {
    case 'normal':
      return 'text-green-400';
    case 'brownout':
    case 'degraded':
      return 'text-yellow-400';
    case 'emergency':
    case 'lockdown':
      return 'text-red-400';
    default:
      return 'text-gray-400';
  }
};

export const getGuardianStatusMessage = (status: string): string => {
  switch (status) {
    case 'normal':
      return 'All systems operational';
    case 'brownout':
      return 'Using lighter processing for faster responses';
    case 'degraded':
      return 'Some features temporarily limited';
    case 'emergency':
      return 'System under high load';
    case 'lockdown':
      return 'Manual intervention required';
    default:
      return 'Status unknown';
  }
};
