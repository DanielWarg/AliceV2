import { useState, useEffect } from 'react';
import { Alert, AlertDescription } from './ui/alert';
import { cn } from '../lib/utils';
import type { GuardianStatus, GuardianState } from '@alice/types';

interface GuardianStatusBannerProps {
  status?: GuardianStatus;
  className?: string;
  onClose?: () => void;
}

const guardianStateConfig = {
  normal: {
    color: 'bg-green-50 border-green-200 text-green-800',
    icon: '✅',
    title: 'System Normal',
    description: 'All systems operating normally',
  },
  brownout: {
    color: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    icon: '⚡',
    title: 'Brownout Mode',
    description: 'Operating with reduced performance to save resources',
  },
  degraded: {
    color: 'bg-orange-50 border-orange-200 text-orange-800',
    icon: '⚠️',
    title: 'Degraded Performance',
    description: 'System experiencing performance issues',
  },
  emergency: {
    color: 'bg-red-50 border-red-200 text-red-800',
    icon: '🚨',
    title: 'Emergency Mode',
    description: 'Critical system issues detected',
  },
  lockdown: {
    color: 'bg-red-100 border-red-300 text-red-900',
    icon: '🔒',
    title: 'System Lockdown',
    description: 'System locked down for protection',
  },
};

export function GuardianStatusBanner({ status, className, onClose }: GuardianStatusBannerProps) {
  const [isVisible, setIsVisible] = useState(true);

  // Only show banner for non-normal states
  if (!status || status.status === 'normal' || !isVisible) {
    return null;
  }

  const config = guardianStateConfig[status.status];

  const handleClose = () => {
    setIsVisible(false);
    onClose?.();
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  return (
    <Alert className={cn(config.color, 'border-l-4', className)}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <span className="text-lg">{config.icon}</span>
          <div>
            <AlertDescription className="font-semibold">{config.title}</AlertDescription>
            <AlertDescription className="text-sm mt-1">{config.description}</AlertDescription>

            {/* Detailed metrics for critical states */}
            {(status.status === 'emergency' || status.status === 'degraded') && (
              <div className="mt-2 text-xs space-y-1">
                <div className="flex space-x-4">
                  <span>RAM: {status.metrics.ram_pct}%</span>
                  <span>CPU: {status.metrics.cpu_pct}%</span>
                  <span>Temp: {status.metrics.temp_c}°C</span>
                </div>
                <div>State Duration: {formatDuration(status.state_duration_s)}</div>
              </div>
            )}

            {/* Brownout specific info */}
            {status.status === 'brownout' && status.brownout && (
              <div className="mt-2 text-xs">
                <div>Level: {status.brownout.level}</div>
                <div>Duration: {formatDuration(status.brownout.duration_s)}</div>
                <div>Model: {status.brownout.config.model_fallback}</div>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={handleClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close banner"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </Alert>
  );
}
