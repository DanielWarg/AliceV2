import type { ASREvent, ASRWebSocketMessage, VoiceSession } from '@alice/types'

export interface WebSocketClientConfig {
  url: string
  reconnectAttempts?: number
  reconnectDelay?: number
  heartbeatInterval?: number
}

export type ASREventCallback = (event: ASREvent) => void

export class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts: number
  private reconnectDelay: number
  private heartbeatInterval: number
  private heartbeatTimer: any = null
  private connecting = false
  private eventCallbacks: Map<string, ASREventCallback[]> = new Map()

  constructor(private config: WebSocketClientConfig) {
    this.maxReconnectAttempts = config.reconnectAttempts || 5
    this.reconnectDelay = config.reconnectDelay || 1000
    this.heartbeatInterval = config.heartbeatInterval || 30000
  }

  async connect(): Promise<void> {
    if (this.connecting || this.isConnected()) {
      return
    }

    this.connecting = true

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url)
        
        this.ws.onopen = () => {
          console.log('WebSocket connected')
          this.connecting = false
          this.reconnectAttempts = 0
          this.startHeartbeat()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data: ASREvent = JSON.parse(event.data)
            this.handleMessage(data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.connecting = false
          this.stopHeartbeat()
          
          if (event.code !== 1000) { // Not a normal close
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.connecting = false
          reject(error)
        }

      } catch (error) {
        this.connecting = false
        reject(error)
      }
    })
  }

  private handleMessage(event: ASREvent) {
    const callbacks = this.eventCallbacks.get(event.event) || []
    const allCallbacks = this.eventCallbacks.get('*') || []
    
    const combinedCallbacks = callbacks.concat(allCallbacks)
    combinedCallbacks.forEach(callback => {
      try {
        callback(event)
      } catch (error) {
        console.error('Error in WebSocket event callback:', error)
      }
    })
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts) // Exponential backoff
    this.reconnectAttempts++

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error)
      })
    }, delay)
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'start_listening' })
      }
    }, this.heartbeatInterval)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  send(message: ASRWebSocketMessage): void {
    if (!this.isConnected()) {
      throw new Error('WebSocket is not connected')
    }

    this.ws!.send(JSON.stringify(message))
  }

  // ASR-specific methods
  startListening(): void {
    this.send({ type: 'start_listening' })
  }

  stopListening(): void {
    this.send({ type: 'stop_listening' })  
  }

  sendAudioChunk(audioData: string, timestamp?: number): void {
    this.send({
      type: 'audio',
      audio: audioData,
      timestamp: timestamp || Date.now()
    })
  }

  updateConfig(config: { language?: string, model?: string }): void {
    this.send({
      type: 'config',
      config
    })
  }

  // Event handling
  on(eventType: string | '*', callback: ASREventCallback): void {
    if (!this.eventCallbacks.has(eventType)) {
      this.eventCallbacks.set(eventType, [])
    }
    this.eventCallbacks.get(eventType)!.push(callback)
  }

  off(eventType: string, callback?: ASREventCallback): void {
    if (!callback) {
      this.eventCallbacks.delete(eventType)
      return
    }

    const callbacks = this.eventCallbacks.get(eventType) || []
    const index = callbacks.indexOf(callback)
    if (index > -1) {
      callbacks.splice(index, 1)
    }
  }

  // Connection state
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  isConnecting(): boolean {
    return this.ws?.readyState === WebSocket.CONNECTING || false
  }

  getState(): string {
    if (!this.ws) return 'disconnected'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'closed'
      default: return 'unknown'
    }
  }

  // Cleanup
  disconnect(): void {
    this.stopHeartbeat()
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    
    this.eventCallbacks.clear()
    this.reconnectAttempts = 0
    this.connecting = false
  }
}