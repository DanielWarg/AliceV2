import { useState, useEffect } from 'react'
import { Card, CardContent } from './Card'
import { Badge } from './Badge'
import { Progress } from './Progress'
import { cn } from '../lib/utils'
import type { PerformanceMetrics } from '@alice/types'

interface PerformanceHUDProps {
  className?: string
  isVisible?: boolean
  onToggle?: () => void
}

export function PerformanceHUD({ 
  className, 
  isVisible = false, 
  onToggle 
}: PerformanceHUDProps) {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Mock data - in real implementation, this would come from API
  useEffect(() => {
    const fetchMetrics = () => {
      // Simulate API call with realistic data
      setTimeout(() => {
        setMetrics({
          ram_usage_mb: Math.floor(Math.random() * 2000) + 1000,
          cpu_usage_pct: Math.floor(Math.random() * 30) + 15,
          disk_usage_pct: Math.floor(Math.random() * 20) + 45,
          response_time_ms: Math.floor(Math.random() * 150) + 50,
          cache_hit_rate: Math.random() * 0.3 + 0.7,
          active_connections: Math.floor(Math.random() * 10) + 2,
          requests_per_minute: Math.floor(Math.random() * 50) + 25
        })
        setIsLoading(false)
      }, 500)
    }

    fetchMetrics()
    
    // Update every 5 seconds when visible
    if (isVisible) {
      const interval = setInterval(fetchMetrics, 5000)
      return () => clearInterval(interval)
    }
  }, [isVisible])

  if (!isVisible) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-4 right-4 z-50 bg-gray-900 text-white p-2 rounded-full shadow-lg hover:bg-gray-800 transition-colors"
        aria-label="Show performance metrics"
      >
        📊
      </button>
    )
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes}MB`
    return `${(bytes / 1024).toFixed(1)}GB`
  }

  const getPerformanceStatus = (value: number, thresholds: { good: number, warning: number }) => {
    if (value <= thresholds.good) return 'good'
    if (value <= thresholds.warning) return 'warning'
    return 'critical'
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-600'
      case 'warning': return 'text-yellow-600'
      case 'critical': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <Card className={cn("fixed bottom-4 right-4 z-50 w-80 shadow-xl", className)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-sm">Performance Monitor</h3>
          <button
            onClick={onToggle}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Hide performance metrics"
          >
            ✕
          </button>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-2 bg-gray-200 rounded"></div>
            </div>
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-2/3 mb-2"></div>
              <div className="h-2 bg-gray-200 rounded"></div>
            </div>
          </div>
        ) : metrics ? (
          <div className="space-y-3">
            {/* RAM Usage */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span>RAM Usage</span>
                <span className={getStatusColor(getPerformanceStatus(metrics.ram_usage_mb, { good: 1500, warning: 2500 }))}>
                  {formatBytes(metrics.ram_usage_mb)}
                </span>
              </div>
              <Progress 
                value={(metrics.ram_usage_mb / 4000) * 100} 
                className="h-2"
              />
            </div>

            {/* CPU Usage */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span>CPU Usage</span>
                <span className={getStatusColor(getPerformanceStatus(metrics.cpu_usage_pct, { good: 30, warning: 60 }))}>
                  {metrics.cpu_usage_pct}%
                </span>
              </div>
              <Progress 
                value={metrics.cpu_usage_pct} 
                className="h-2"
              />
            </div>

            {/* Response Time */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span>Response Time</span>
                <span className={getStatusColor(getPerformanceStatus(metrics.response_time_ms, { good: 100, warning: 300 }))}>
                  {metrics.response_time_ms}ms
                </span>
              </div>
              <Progress 
                value={Math.min((metrics.response_time_ms / 500) * 100, 100)}
                className="h-2"
              />
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-100">
              <div className="text-center">
                <div className="text-xs text-gray-500">Cache Hit Rate</div>
                <Badge variant="outline" className="text-xs">
                  {(metrics.cache_hit_rate * 100).toFixed(1)}%
                </Badge>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-500">Connections</div>
                <Badge variant="outline" className="text-xs">
                  {metrics.active_connections}
                </Badge>
              </div>
            </div>

            {/* Requests per minute */}
            <div className="text-center text-xs text-gray-500">
              {metrics.requests_per_minute} requests/min
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}