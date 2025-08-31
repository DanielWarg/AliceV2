import { useState, useRef, useEffect } from 'react'
import { Button } from './Button'
import { cn } from '../lib/utils'
import type { VoiceSession } from '@alice/types'

interface VoiceCommandInterfaceProps {
  onCommand?: (command: string) => Promise<string>
  className?: string
}

interface VoiceCommandSession {
  active: boolean
  intent: string
  startTime: number
  resultText?: string
  processing: boolean
}

export function VoiceCommandInterface({ onCommand, className }: VoiceCommandInterfaceProps) {
  const [session, setSession] = useState<VoiceCommandSession | null>(null)
  const [cacheStats, setCacheStats] = useState({ cached_phrases: 0, cache_keys: [] })
  const [isWarming, setIsWarming] = useState(false)
  
  // Audio elements for ack and result
  const ackAudioRef = useRef<HTMLAudioElement>(null)
  const resultAudioRef = useRef<HTMLAudioElement>(null)
  
  // Voice settings
  const voice = "nova"
  const rate = 1.0

  /**
   * Execute voice command with processing flow
   */
  const executeVoiceCommand = async (
    intent: string, 
    command: string, 
    params: Record<string, string | number> = {},
    customHandler?: () => Promise<string>
  ) => {
    const sessionStart = Date.now()
    
    setSession({
      active: true,
      intent,
      startTime: sessionStart,
      processing: true
    })
    
    try {
      // Execute command
      console.log(`🧠 Processing command: ${command}`)
      const result = customHandler 
        ? await customHandler()
        : onCommand 
        ? await onCommand(command) 
        : `Mock result for: ${command}`
      
      // Update session with result
      setSession(prev => prev ? {
        ...prev,
        resultText: result,
        active: false,
        processing: false
      } : null)
      
      const totalTime = Date.now() - sessionStart
      console.log(`✅ Voice command complete: ${totalTime}ms total`)
      
    } catch (error) {
      console.error("Voice command failed:", error)
      setSession(prev => prev ? { 
        ...prev, 
        active: false, 
        processing: false,
        resultText: "Error processing command"
      } : null)
    }
  }
  
  /**
   * Command handlers
   */
  const commandHandlers: Record<string, () => Promise<string>> = {
    email: async () => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      return "You have 3 new emails from your team."
    },
    
    calendar: async () => {
      await new Promise(resolve => setTimeout(resolve, 800))
      return "Your calendar is clear for today."
    },
    
    weather: async () => {
      await new Promise(resolve => setTimeout(resolve, 1200))
      return "It's 19 degrees and partly cloudy in Stockholm right now."
    },
    
    timer: async () => {
      await new Promise(resolve => setTimeout(resolve, 500))
      return "Timer set for 10 minutes. I'll let you know when it's done."
    },
    
    music: async () => {
      await new Promise(resolve => setTimeout(resolve, 900))
      return "Playing your liked songs. Now playing music for you."
    },
    
    search: async () => {
      await new Promise(resolve => setTimeout(resolve, 1500))
      return "AI is a broad field covering machine learning, neural networks, and intelligent systems."
    }
  }

  /**
   * Handle different voice scenarios
   */
  const handleScenario = (scenario: string) => {
    if (session?.active) return

    switch (scenario) {
      case "email":
        executeVoiceCommand("mail.check_unread", "Check my unread emails", {}, commandHandlers.email)
        break
      case "calendar":
        executeVoiceCommand("calendar.today", "What's on my calendar today?", {}, commandHandlers.calendar)
        break
      case "weather":
        executeVoiceCommand("weather.current", "What's the weather in Stockholm?", { city: "Stockholm" }, commandHandlers.weather)
        break
      case "timer":
        executeVoiceCommand("timer.set", "Set a timer for 10 minutes", { duration: "10 minutes" }, commandHandlers.timer)
        break
      case "music":
        executeVoiceCommand("spotify.play", "Play some music", {}, commandHandlers.music)
        break
      case "search":
        executeVoiceCommand("general.search", "Search for information about AI", {}, commandHandlers.search)
        break
      default:
        executeVoiceCommand("default", `Unknown command: ${scenario}`)
    }
  }
  
  return (
    <div className={cn("voice-command-interface bg-white border border-gray-200 rounded-lg p-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">
          🎙️ Voice Commands
        </h2>
      </div>
      
      {/* Current Session Status */}
      {session && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-blue-900">
                Current Session: {session.intent}
              </h3>
              {session.processing && (
                <p className="text-sm text-blue-700">
                  🎵 Processing... ({Math.round((Date.now() - session.startTime) / 1000)}s)
                </p>
              )}
              {session.resultText && !session.processing && (
                <p className="text-sm text-green-700">
                  ✅ Complete: "{session.resultText}"
                </p>
              )}
            </div>
            
            {session.processing && (
              <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
            )}
          </div>
        </div>
      )}
      
      {/* Command Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          onClick={() => handleScenario("email")}
          disabled={session?.active}
          variant="outline"
          className="p-3 h-auto flex flex-col items-center space-y-1"
        >
          <span className="text-lg">📧</span>
          <span className="text-sm">Check Email</span>
        </Button>
        
        <Button
          onClick={() => handleScenario("calendar")}
          disabled={session?.active}
          variant="outline"
          className="p-3 h-auto flex flex-col items-center space-y-1"
        >
          <span className="text-lg">📅</span>
          <span className="text-sm">Today's Calendar</span>
        </Button>
        
        <Button
          onClick={() => handleScenario("weather")}
          disabled={session?.active}
          variant="outline"
          className="p-3 h-auto flex flex-col items-center space-y-1"
        >
          <span className="text-lg">🌤️</span>
          <span className="text-sm">Weather</span>
        </Button>
        
        <Button
          onClick={() => handleScenario("timer")}
          disabled={session?.active}
          variant="outline"
          className="p-3 h-auto flex flex-col items-center space-y-1"
        >
          <span className="text-lg">⏰</span>
          <span className="text-sm">Set Timer</span>
        </Button>
        
        <Button
          onClick={() => handleScenario("music")}
          disabled={session?.active}
          variant="outline"
          className="p-3 h-auto flex flex-col items-center space-y-1"
        >
          <span className="text-lg">🎵</span>
          <span className="text-sm">Play Music</span>
        </Button>
        
        <Button
          onClick={() => handleScenario("search")}
          disabled={session?.active}
          variant="outline"
          className="p-3 h-auto flex flex-col items-center space-y-1"
        >
          <span className="text-lg">🔍</span>
          <span className="text-sm">Search</span>
        </Button>
      </div>
      
      {/* Audio Elements */}
      <div className="hidden">
        <audio 
          ref={ackAudioRef}
          preload="none"
          onError={(e) => console.error("Ack audio error:", e)}
        />
        <audio 
          ref={resultAudioRef}
          preload="none"
          onError={(e) => console.error("Result audio error:", e)}
        />
      </div>
      
      {/* Debug Info */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-6 p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm">
          <h4 className="font-medium text-gray-700 mb-2">Debug Info:</h4>
          <div className="space-y-1 text-gray-600">
            <p>Voice: {voice} | Rate: {rate}</p>
            {session && (
              <p>Session: {session.intent} | Active: {session.active}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}