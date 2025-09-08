# 🎨 Alice v2 Frontend Development Guide
*Complete Guide for Building React/Next.js Interface for Production-Ready AI System*

## 🚨 CRITICAL CONTEXT

**Alice v2 is NOT a chatbot project.** This is an **enterprise-grade, self-improving AI assistant** with:

- ✅ **T1-T9 RL/ML Systems Complete** (90%+ done) - LinUCB routing, Thompson sampling, φ-Fibonacci optimization
- ✅ **Guardian Brownout Protection** - NORMAL/BROWNOUT/EMERGENCY states with automatic kill sequences
- ✅ **Swedish NLU Engine** - 88%+ accuracy with E5 embeddings + XNLI fallback
- ✅ **Smart Cache L1/L2/L3** - Semantic matching with telemetry-driven optimization  
- ✅ **Enterprise Security** - PII masking, policy enforcement, audit trails
- ✅ **Full Observability** - P50/P95 metrics, energy tracking, comprehensive telemetry
- ❌ **Frontend Completely Removed** - Need React/Next.js interface from scratch
- ❌ **Voice Service Broken** - Restart loop on port 8002 (separate priority)

**Mission**: Build a modern React/Next.js web interface that exposes this sophisticated AI system to users.

---

## 🏗️ System Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │           FRONTEND LAYER            │
                    │        (NEEDS TO BE BUILT)          │
                    │                                     │
                    │  ┌─────────────┐  ┌─────────────┐   │
                    │  │  React/WS   │  │   Mobile    │   │
                    │  │   Web UI    │  │    Ready    │   │
                    │  │ (Port 3000) │  │             │   │
                    │  └─────────────┘  └─────────────┘   │
                    └─────────────┬───────────────────────┘
                                  │ HTTP/WebSocket
    ┌─────────────────────────────▼─────────────────────────────┐
    │                 ALICE v2 ENTERPRISE CORE                   │
    │                    (90%+ COMPLETE)                         │
    │                                                            │
    │  Orchestrator (8001) ◄──► Guardian (8787) ◄──► NLU (9002) │
    │  LangGraph Router         Brownout Protection   Swedish    │
    │  T4-T9 RL/ML             Kill Sequences         88% Acc   │
    │        │                       │                    │     │
    │        ▼                       ▼                    ▼     │
    │  Smart Cache L1/L2/L3    Security/PII         Telemetry   │
    │  Redis (6379)            Policy Engine        P50/P95     │
    │  Semantic Matching       Audit Trails         Energy      │
    └────────────────────────────────────────────────────────────┘
```

---

## 🎯 Frontend Requirements

### Core User Experience
1. **Chat Interface** - Clean, modern conversation UI
2. **Voice Integration** - WebSocket connection to voice service (when fixed)  
3. **System Status** - Real-time Guardian state and system health
4. **Performance Monitoring** - Live telemetry and P50/P95 metrics
5. **Settings Panel** - User preferences and system configuration
6. **Swedish Language Support** - Native Swedish UI and content handling

### Advanced Features
1. **RL Optimization Visibility** - Show T4-T9 intelligence in action
2. **Guardian Protection UI** - Brownout state awareness and user feedback
3. **Memory Management** - User memory controls and data governance
4. **Tool Orchestration** - Visual representation of MCP tool usage
5. **Energy Tracking** - Power usage and efficiency metrics display
6. **Cache Analytics** - Smart cache performance insights

---

## 📁 Recommended File Structure

```
apps/web/                           # Main Next.js application
├── src/
│   ├── app/                        # Next.js 13+ App Router
│   │   ├── globals.css            # Global styles + Alice branding
│   │   ├── layout.tsx             # Root layout with providers
│   │   ├── page.tsx               # Main chat interface
│   │   ├── chat/                  # Chat-related pages
│   │   ├── settings/              # User settings pages
│   │   ├── monitoring/            # System monitoring dashboard
│   │   └── api/                   # API routes (proxy to services)
│   ├── components/                 # React components
│   │   ├── chat/                  # Chat interface components
│   │   │   ├── ChatInterface.tsx  # Main chat component
│   │   │   ├── MessageBubble.tsx  # Individual message display
│   │   │   ├── InputArea.tsx      # Message input with voice
│   │   │   ├── TypingIndicator.tsx
│   │   │   └── MessageHistory.tsx
│   │   ├── voice/                 # Voice interface components  
│   │   │   ├── VoiceButton.tsx    # Push-to-talk button
│   │   │   ├── AudioVisualizer.tsx# Audio waveform display
│   │   │   ├── VoiceStatus.tsx    # Recording/processing status
│   │   │   └── TTSPlayer.tsx      # Text-to-speech playback
│   │   ├── system/                # System status components
│   │   │   ├── GuardianStatus.tsx # System health indicator
│   │   │   ├── PerformanceHUD.tsx # P50/P95 metrics display
│   │   │   ├── EnergyTracker.tsx  # Power usage monitoring
│   │   │   └── SystemAlerts.tsx   # Brownout/emergency notices
│   │   ├── monitoring/            # Advanced monitoring
│   │   │   ├── TelemetryDash.tsx  # Real-time telemetry
│   │   │   ├── RLMetrics.tsx      # RL/ML optimization stats
│   │   │   ├── CacheAnalytics.tsx # Cache performance
│   │   │   └── MemoryInsights.tsx # User memory analytics
│   │   └── ui/                    # Base UI components (shadcn/ui)
│   │       ├── button.tsx
│   │       ├── input.tsx  
│   │       ├── card.tsx
│   │       ├── alert.tsx
│   │       └── ...
│   ├── lib/                       # Utilities and configuration
│   │   ├── api.ts                 # Alice API SDK integration
│   │   ├── websocket.ts           # WebSocket management
│   │   ├── voice-client.ts        # Voice service client
│   │   ├── utils.ts               # Common utilities
│   │   └── constants.ts           # App constants
│   ├── hooks/                     # Custom React hooks
│   │   ├── useAliceAPI.ts         # Alice API integration
│   │   ├── useVoice.ts            # Voice interface
│   │   ├── useGuardianStatus.ts   # System health monitoring
│   │   ├── useTelemetry.ts        # Real-time metrics
│   │   └── useWebSocket.ts        # WebSocket connection
│   ├── store/                     # State management (Zustand)
│   │   ├── chatStore.ts           # Chat state management
│   │   ├── systemStore.ts         # System status state
│   │   ├── settingsStore.ts       # User settings
│   │   └── voiceStore.ts          # Voice interface state
│   └── types/                     # TypeScript definitions
│       ├── alice.ts               # Alice API types
│       ├── chat.ts                # Chat interface types
│       ├── voice.ts               # Voice service types
│       └── system.ts              # System monitoring types
├── public/                        # Static assets
│   ├── alice-logo.svg            # Alice branding
│   ├── icons/                    # System status icons
│   └── sounds/                   # UI sound effects
├── package.json                  # Dependencies
├── next.config.js               # Next.js configuration
├── tailwind.config.js           # Tailwind CSS config
└── tsconfig.json                # TypeScript config
```

---

## 🛠️ Technology Stack

### Core Framework
- **Next.js 13+** with App Router - Modern React framework
- **React 18** - Latest React with concurrent features
- **TypeScript** - Type safety throughout the application
- **Tailwind CSS** - Utility-first styling for rapid development

### UI Components  
- **shadcn/ui** - High-quality, accessible React components
- **Lucide React** - Modern icon library
- **Framer Motion** - Smooth animations and transitions
- **React Hook Form** - Forms with validation

### State Management
- **Zustand** - Lightweight state management
- **React Query/TanStack Query** - Server state synchronization
- **React Context** - Global app state (theme, settings)

### Real-time Communication
- **WebSocket API** - Native browser WebSocket for voice
- **EventSource/SSE** - Server-sent events for telemetry
- **Alice API SDK** - Type-safe API client (@alice/api package)

### Voice & Audio
- **Web Audio API** - Audio processing and visualization
- **MediaRecorder API** - Audio recording for voice input
- **Web Speech API** - Browser speech synthesis fallback

---

## 🔌 Integration Points

### 1. Orchestrator API Integration (Port 8001)
```typescript
// lib/api.ts
import { createAliceClients } from '@alice/api';

export const aliceClients = createAliceClients({
  orchestratorURL: 'http://localhost:8001',
  guardianURL: 'http://localhost:8787',
  defaultSessionId: 'web-interface',
  timeout: 5000,
  maxRetries: 3,
});

// Main chat API calls
export async function sendChatMessage(message: string, sessionId: string) {
  return await aliceClients.orchestrator.chat({
    message,
    sessionId,
    metadata: {
      source: 'web-ui',
      timestamp: Date.now(),
    }
  });
}

export async function getChatHistory(sessionId: string) {
  return await aliceClients.orchestrator.getHistory(sessionId);
}
```

### 2. Guardian Status Integration (Port 8787)
```typescript  
// hooks/useGuardianStatus.ts
import { useQuery } from '@tanstack/react-query';
import { aliceClients } from '@/lib/api';

export function useGuardianStatus() {
  return useQuery({
    queryKey: ['guardian-status'],
    queryFn: () => aliceClients.guardian.getStatus(),
    refetchInterval: 1000, // Check every second
    staleTime: 500,
  });
}

// components/system/GuardianStatus.tsx  
export function GuardianStatus() {
  const { data: status } = useGuardianStatus();
  
  const statusConfig = {
    NORMAL: { color: 'green', icon: CheckCircle, text: 'System Healthy' },
    BROWNOUT: { color: 'yellow', icon: AlertTriangle, text: 'Performance Reduced' },
    EMERGENCY: { color: 'red', icon: AlertCircle, text: 'Emergency Mode' },
  };
  
  const config = statusConfig[status?.state || 'NORMAL'];
  
  return (
    <Alert className={`border-${config.color}-500`}>
      <config.icon className="h-4 w-4" />
      <AlertDescription>{config.text}</AlertDescription>
    </Alert>
  );
}
```

### 3. NLU Swedish Processing (Port 9002)
```typescript
// hooks/useNLUProcessing.ts
export function useNLUProcessing() {
  return useMutation({
    mutationFn: async (text: string) => {
      const response = await fetch('http://localhost:9002/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text, 
          language: 'sv',
          source: 'web-interface' 
        }),
      });
      return response.json();
    }
  });
}
```

### 4. Voice Service Integration (Port 8002) - When Fixed
```typescript
// lib/voice-client.ts
export class AliceVoiceClient {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext;
  private mediaRecorder: MediaRecorder | null = null;
  
  constructor() {
    this.audioContext = new AudioContext();
  }
  
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket('ws://localhost:8002/ws/stream');
      
      this.ws.onopen = () => {
        console.log('🎙️ Voice pipeline connected');
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleVoiceEvent(data);
      };
      
      this.ws.onerror = reject;
    });
  }
  
  async generateTTS(text: string): Promise<ArrayBuffer> {
    const response = await fetch('http://localhost:8002/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    
    return await response.arrayBuffer();
  }
  
  startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        this.mediaRecorder = new MediaRecorder(stream);
        this.mediaRecorder.start();
        
        this.mediaRecorder.ondataavailable = (event) => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(event.data);
          }
        };
      });
  }
}
```

### 5. Smart Cache Integration (Port 6379)
```typescript
// hooks/useCacheMetrics.ts  
export function useCacheMetrics() {
  return useQuery({
    queryKey: ['cache-metrics'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8001/api/cache/metrics');
      return response.json();
    },
    refetchInterval: 5000,
  });
}

// components/monitoring/CacheAnalytics.tsx
export function CacheAnalytics() {
  const { data: metrics } = useCacheMetrics();
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Smart Cache Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Hit Rate</p>
            <p className="text-2xl font-bold">{metrics?.hitRate || 0}%</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">L1 Cache</p>
            <p className="text-2xl font-bold">{metrics?.l1Hits || 0}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Semantic Matches</p>
            <p className="text-2xl font-bold">{metrics?.semanticHits || 0}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 6. Telemetry and Performance Monitoring
```typescript
// hooks/useTelemetry.ts
export function useTelemetry() {
  const [metrics, setMetrics] = useState<TelemetryData | null>(null);
  
  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8001/api/telemetry/stream');
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMetrics(data);
    };
    
    return () => eventSource.close();
  }, []);
  
  return metrics;
}

// components/monitoring/PerformanceHUD.tsx
export function PerformanceHUD() {
  const telemetry = useTelemetry();
  
  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard 
        title="P95 Latency"
        value={`${telemetry?.p95_latency_ms || 0}ms`}
        status={telemetry?.p95_latency_ms < 1500 ? 'good' : 'warning'}
      />
      <MetricCard 
        title="Energy/Turn"
        value={`${telemetry?.wh_per_turn || 0}Wh`}
        status={telemetry?.wh_per_turn < 0.5 ? 'good' : 'warning'}
      />
      <MetricCard 
        title="RL Router Success"
        value={`${telemetry?.rl_success_rate || 0}%`}
        status={telemetry?.rl_success_rate > 95 ? 'good' : 'warning'}
      />
      <MetricCard 
        title="NLU Accuracy"
        value={`${telemetry?.nlu_accuracy || 0}%`}
        status={telemetry?.nlu_accuracy > 88 ? 'good' : 'warning'}
      />
    </div>
  );
}
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation Setup (Week 1)
**Goal**: Basic Next.js app with Alice API integration

#### Tasks:
1. **Project Initialization**
   ```bash
   # Create Next.js app with TypeScript
   cd apps/
   npx create-next-app@latest web --typescript --tailwind --eslint --app
   cd web
   npm install @alice/api @alice/types @alice/ui
   ```

2. **Basic UI Structure**
   - Set up layout with Alice branding
   - Create basic chat interface skeleton
   - Implement shadcn/ui components
   - Add responsive design foundation

3. **API Integration**
   - Connect to Orchestrator API (port 8001)
   - Implement basic chat functionality
   - Add error handling and loading states
   - Set up TypeScript types from @alice/types

4. **State Management**
   - Configure Zustand stores for chat state
   - Add React Query for server state
   - Implement basic session management

**Success Criteria**:
- ✅ User can send and receive chat messages
- ✅ Basic Alice branding and responsive layout
- ✅ TypeScript compilation without errors
- ✅ Working connection to Orchestrator API

### Phase 2: System Integration (Week 2)
**Goal**: Connect to Guardian, NLU, and monitoring systems

#### Tasks:
1. **Guardian Integration**
   - Real-time system health monitoring
   - Brownout state user notifications
   - Emergency mode handling and user feedback

2. **NLU Swedish Support**
   - Show intent classification results
   - Display confidence scores
   - Handle Swedish language properly in UI

3. **Performance Monitoring**
   - Real-time P50/P95 metrics display
   - Energy tracking visualization
   - Cache performance insights

4. **Advanced Chat Features**
   - Message history persistence
   - Session management
   - User preferences and settings

**Success Criteria**:
- ✅ Real-time Guardian status displayed
- ✅ Swedish NLU integration working
- ✅ Performance metrics visible to users
- ✅ Stable session management

### Phase 3: Voice Integration (Week 3) - Depends on Voice Service Fix
**Goal**: Complete voice interface integration

#### Tasks:
1. **Voice Service Connection**
   - WebSocket connection to voice service
   - Audio recording and streaming
   - Real-time transcription display

2. **TTS Playback**
   - Swedish text-to-speech integration
   - Audio visualization components
   - Voice activity detection UI

3. **Voice UI/UX**
   - Push-to-talk button design
   - Recording status indicators
   - Audio waveform visualization

4. **Voice Settings**
   - Audio device selection
   - Voice processing preferences
   - TTS voice configuration

**Success Criteria**:
- ✅ Voice recording and transcription working
- ✅ TTS playback with Swedish voices
- ✅ Intuitive voice interface design
- ✅ Voice settings and preferences

### Phase 4: Advanced Features (Week 4)
**Goal**: Expose advanced AI capabilities in the UI

#### Tasks:
1. **RL/ML Visualization**
   - Show T4-T9 system intelligence in action
   - Route selection visualization (micro/planner/deep)
   - Thompson sampling and bandit learning insights

2. **Memory Management**
   - User memory browser and search
   - Privacy controls and data governance
   - "Forget me" functionality

3. **Tool Orchestration**
   - Visual representation of MCP tools
   - Tool execution status and results
   - Tool configuration and management

4. **Analytics Dashboard**
   - Advanced telemetry visualization
   - System performance trends
   - Usage analytics and insights

**Success Criteria**:
- ✅ Users can see AI intelligence in action
- ✅ Complete memory management interface
- ✅ Tool orchestration is transparent
- ✅ Rich analytics and monitoring

---

## 📱 User Interface Design

### Main Chat Interface
- **Clean, modern design** similar to ChatGPT but with Alice branding
- **Swedish language first** - All UI text available in Swedish
- **Guardian status indicator** always visible (green/yellow/red dot)
- **Performance metrics** in footer (P95 latency, energy per turn)
- **Voice button** prominently placed (when voice service is fixed)

### System Status Panel
- **Real-time Guardian state** with visual indicators
- **Service health checks** for all backend services
- **Performance metrics** with historical trends
- **Alert notifications** for brownout/emergency states

### Settings and Preferences
- **Language selection** (Swedish primary, English fallback)
- **Voice settings** (TTS voice, audio devices)
- **Privacy controls** (memory management, data retention)
- **System preferences** (theme, notifications, advanced features)

---

## 🔐 Security Considerations

### Data Protection
- **PII Masking**: Integrate with Alice security policies
- **Session Security**: Secure session tokens and authentication
- **HTTPS Only**: Enforce secure connections in production
- **CORS Policy**: Proper cross-origin resource sharing configuration

### Privacy Features
- **Memory Controls**: Let users manage their data
- **Consent Management**: GDPR-compliant data handling
- **Data Export**: Allow users to download their data
- **Right to be Forgotten**: Implement data deletion

---

## 🧪 Testing Strategy

### Unit Testing
- **React Components**: Jest + React Testing Library
- **Hooks**: Custom hook testing utilities
- **API Integration**: Mock Alice API responses
- **State Management**: Zustand store testing

### Integration Testing
- **API Connectivity**: Test all service integrations
- **WebSocket Communication**: Voice and real-time data
- **Error Handling**: Network failures and service outages
- **Performance**: Load testing with real backend

### E2E Testing
- **User Workflows**: Complete chat conversations
- **Voice Integration**: End-to-end voice testing (when available)
- **System Monitoring**: Guardian state changes
- **Multi-language**: Swedish and English interfaces

---

## 📊 Performance Requirements

### Core Performance Targets
- **Initial Load**: <2 seconds to first interactive
- **Chat Response**: <500ms UI response to user input
- **Real-time Updates**: <100ms latency for system status
- **Memory Usage**: <100MB for typical chat sessions

### Advanced Performance Features
- **Progressive Loading**: Lazy load heavy components
- **Caching Strategy**: Cache API responses and assets
- **Bundle Optimization**: Code splitting and tree shaking
- **Service Workers**: Offline functionality where possible

---

## 🚀 Deployment Configuration

### Development Environment
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/orchestrator/:path*',
        destination: 'http://localhost:8001/:path*'
      },
      {
        source: '/api/guardian/:path*', 
        destination: 'http://localhost:8787/:path*'
      },
      {
        source: '/api/nlu/:path*',
        destination: 'http://localhost:9002/:path*'
      },
      {
        source: '/api/voice/:path*',
        destination: 'http://localhost:8002/:path*' // When voice is fixed
      }
    ];
  },
  experimental: {
    serverActions: true,
  },
};

module.exports = nextConfig;
```

### Docker Configuration
```dockerfile
# apps/web/Dockerfile
FROM node:18-alpine AS base

# Dependencies
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Build
FROM base AS builder  
WORKDIR /app
COPY . .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

# Runtime
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

### Docker Compose Integration
```yaml
# Add to docker-compose.yml
services:
  alice-web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    container_name: alice-web
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8001
      - NEXT_PUBLIC_GUARDIAN_URL=http://localhost:8787
      - NEXT_PUBLIC_NLU_URL=http://localhost:9002
      - NEXT_PUBLIC_VOICE_URL=http://localhost:8002
    depends_on:
      - orchestrator
      - guardian
      - nlu
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 🔧 Makefile Integration

```make
# Add to project Makefile
.PHONY: web-setup web-dev web-build web-test web-lint

web-setup:
	@echo "🎨 Setting up Alice v2 Web Interface..."
	cd apps/web && npm install
	cd apps/web && npm run prepare

web-dev: 
	@echo "🚀 Starting web development server..."
	cd apps/web && npm run dev

web-build:
	@echo "📦 Building production web interface..."
	cd apps/web && npm run build

web-test:
	@echo "🧪 Running web interface tests..."
	cd apps/web && npm run test

web-lint:
	@echo "🔍 Linting web interface code..."
	cd apps/web && npm run lint

web-e2e:
	@echo "🎭 Running end-to-end tests..."
	cd apps/web && npm run test:e2e

# Combined frontend commands
frontend-setup: web-setup
	@echo "✅ Alice v2 Web Interface ready for development"

frontend-dev: web-dev

frontend-test: web-test web-e2e
	@echo "✅ All frontend tests passed"
```

---

## 📚 Documentation Requirements

### User Documentation
1. **User Guide** - How to use the Alice v2 interface
2. **Voice Guide** - Voice commands and features (when available)
3. **Settings Guide** - System configuration and preferences
4. **Privacy Guide** - Data handling and user controls

### Developer Documentation  
1. **Component Library** - Documented React components
2. **API Integration** - How to connect to Alice services
3. **State Management** - Zustand store patterns
4. **Testing Guide** - How to write and run tests

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ **Complete Chat Interface** - Users can have full conversations with Alice
- ✅ **Real-time System Monitoring** - Guardian status, performance metrics visible
- ✅ **Swedish Language Support** - Native Swedish UI and processing
- ✅ **Voice Integration Ready** - WebSocket connections prepared (when service fixed)
- ✅ **Responsive Design** - Works on desktop, tablet, and mobile
- ✅ **Accessibility** - WCAG 2.1 AA compliance

### Technical Requirements  
- ✅ **TypeScript Coverage** - 100% TypeScript, no any types
- ✅ **Error Handling** - Graceful handling of all failure modes
- ✅ **Performance** - Meets all performance targets
- ✅ **Testing Coverage** - >90% test coverage for critical paths
- ✅ **Security** - Proper HTTPS, CORS, and data handling
- ✅ **Production Ready** - Docker deployment, monitoring, logging

### Integration Requirements
- ✅ **Alice API SDK** - Uses @alice/api package consistently
- ✅ **Service Integration** - Connects to all Alice backend services
- ✅ **Guardian Awareness** - Responds appropriately to system states
- ✅ **Telemetry Integration** - Displays real-time system metrics
- ✅ **Memory Management** - Provides user data controls
- ✅ **Tool Orchestration** - Shows MCP tool usage transparently

---

## 🔗 Related Documentation

- **README.md** - Complete Alice v2 system overview
- **AGENTS.md** - Current system status and service ports
- **VOICE_REACTIVATION_GUIDE.md** - Voice service integration details
- **SYSTEM_INTEGRATION.md** - How all services connect
- **ALICE_SYSTEM_BLUEPRINT.md** - Complete system architecture
- **.cursor/rules/workflow.mdc** - Development workflow requirements
- **packages/api/README.md** - Alice API SDK documentation
- **packages/ui/README.md** - Alice UI component library

---

## 💡 Key Reminders

1. **This is NOT a chatbot** - You're building a UI for an enterprise-grade, self-improving AI system
2. **90% of AI is complete** - Focus on exposing existing capabilities, not building new AI
3. **Swedish-first** - Native Swedish language support throughout
4. **Guardian-aware** - Always respect system protection states
5. **Performance-focused** - This is a production system with real SLOs
6. **Voice-ready** - Prepare for voice integration even if service is currently broken
7. **Security-conscious** - PII protection and privacy controls are critical
8. **Monitoring-rich** - Users should see the sophisticated system at work

---

*Created: 2025-09-08 | Alice v2 Frontend Development Guide*  
*Priority: HIGHEST after Voice Service debugging*  
*Target: Production-ready React/Next.js interface for enterprise AI system*  
*Status: Ready for Implementation*

**🚀 This frontend will expose the magic of Alice v2's T1-T9 self-improving intelligence to the world!**