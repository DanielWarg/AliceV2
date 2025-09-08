import { useState, useEffect, useRef } from 'react'
import { Button } from './Button'
import { cn } from "../utils"
import type { VoiceSession, ASREvent } from '@alice/types'

interface VoiceInterfaceProps {
  onVoiceCommand?: (command: string) => void
  isListening?: boolean
  className?: string
}

export function VoiceInterface({ 
  onVoiceCommand, 
  isListening = false,
  className 
}: VoiceInterfaceProps) {
  const [session, setSession] = useState<VoiceSession>({
    id: '',
    isRecording: false,
    transcript: {
      partial: '',
      final: '',
      confidence: 0
    },
    latency: {},
    status: 'idle'
  })
  
  const [volume, setVolume] = useState(0)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const animationFrameRef = useRef<number>()

  const handleStartListening = async () => {
    try {
      setSession(prev => ({ ...prev, status: 'recording', isRecording: true }))
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      })
      
      mediaStreamRef.current = stream
      
      // Set up audio analysis for visual feedback
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      analyserRef.current.fftSize = 256
      
      // Start volume monitoring
      monitorVolume()
      
    } catch (error) {
      console.error('Error starting voice recording:', error)
      setSession(prev => ({ ...prev, status: 'error', isRecording: false }))
    }
  }

  const handleStopListening = () => {
    setSession(prev => ({ ...prev, status: 'processing', isRecording: false }))
    
    // Stop audio context and stream
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    
    setVolume(0)
    
    // Simulate processing completion
    setTimeout(() => {
      setSession(prev => ({ ...prev, status: 'idle' }))
      if (session.transcript.final && onVoiceCommand) {
        onVoiceCommand(session.transcript.final)
      }
    }, 1000)
  }

  const monitorVolume = () => {
    if (!analyserRef.current) return
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    
    const updateVolume = () => {
      if (!analyserRef.current) return
      
      analyserRef.current.getByteFrequencyData(dataArray)
      const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length
      setVolume(Math.min(average / 128, 1)) // Normalize to 0-1
      
      animationFrameRef.current = requestAnimationFrame(updateVolume)
    }
    
    updateVolume()
  }

  // Handle ASR events (would be connected to WebSocket in real implementation)
  const handleASREvent = (event: ASREvent) => {
    switch (event.event) {
      case 'partial':
        setSession(prev => ({
          ...prev,
          transcript: {
            ...prev.transcript,
            partial: event.text || ''
          }
        }))
        break
        
      case 'final':
        setSession(prev => ({
          ...prev,
          transcript: {
            ...prev.transcript,
            final: event.text || '',
            confidence: event.confidence || 0
          },
          latency: {
            ...prev.latency,
            final_ms: event.asr_latency_ms
          }
        }))
        break
        
      case 'error':
        setSession(prev => ({ 
          ...prev, 
          status: 'error' 
        }))
        break
    }
  }

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [])

  return (
    <div className={cn("flex flex-col items-center space-y-4", className)}>
      {/* Voice Button */}
      <div className="relative">
        <Button
          variant={session.isRecording ? "destructive" : "alice"}
          size="lg"
          onClick={session.isRecording ? handleStopListening : handleStartListening}
          disabled={session.status === 'processing'}
          className={cn(
            "relative w-16 h-16 rounded-full transition-all duration-200",
            session.isRecording && "scale-110",
            session.status === 'processing' && "animate-pulse"
          )}
        >
          {session.status === 'processing' ? (
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : session.isRecording ? (
            <div className="w-4 h-4 bg-white rounded-sm" />
          ) : (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
            </svg>
          )}
        </Button>
        
        {/* Visual feedback ring */}
        {session.isRecording && (
          <div 
            className="absolute inset-0 rounded-full border-4 border-blue-400 animate-ping"
            style={{
              opacity: volume * 0.5 + 0.1,
              transform: `scale(${1 + volume * 0.3})`
            }}
          />
        )}
      </div>

      {/* Status Text */}
      <div className="text-center min-h-[2rem]">
        {session.status === 'idle' && (
          <p className="text-sm text-gray-600">Click to start voice command</p>
        )}
        {session.status === 'recording' && (
          <p className="text-sm text-blue-600 animate-pulse">Listening...</p>
        )}
        {session.status === 'processing' && (
          <p className="text-sm text-orange-600">Processing...</p>
        )}
        {session.status === 'error' && (
          <p className="text-sm text-red-600">Error: Please try again</p>
        )}
      </div>

      {/* Transcript Display */}
      {(session.transcript.partial || session.transcript.final) && (
        <div className="w-full max-w-md p-3 bg-gray-50 rounded-lg">
          {session.transcript.partial && (
            <p className="text-gray-500 italic text-sm">
              {session.transcript.partial}
            </p>
          )}
          {session.transcript.final && (
            <p className="text-gray-900 font-medium">
              {session.transcript.final}
              {session.transcript.confidence > 0 && (
                <span className="ml-2 text-xs text-gray-500">
                  ({Math.round(session.transcript.confidence * 100)}%)
                </span>
              )}
            </p>
          )}
        </div>
      )}

      {/* Latency Info (dev mode) */}
      {process.env.NODE_ENV === 'development' && session.latency.final_ms && (
        <div className="text-xs text-gray-400">
          ASR: {session.latency.final_ms}ms
        </div>
      )}
    </div>
  )
}