# Opus AI Implementation Task: Alice v2 Step 1 - Orchestrator Core

## 🎯 Mission
Implement **Step 1: Orchestrator Core (LangGraph) + API-kontrakt + klient-SDK** according to Alice v2 specifications.

## 📋 Context & Background

You are implementing the foundational component of Alice v2 - a modular AI assistant with deterministic safety. This is **Step 1 of 17** in our professional development roadmap.

**Why Step 1 First**: All other components plug into the Orchestrator. Without stable API contracts, the rest becomes spaghetti code. This creates the backbone that Guardian, Voice, Memory, and Frontend will communicate through.

## 📊 Current Project State

**Architecture**: Complete (see ALICE_SYSTEM_BLUEPRINT.md)  
**Development Setup**: Monorepo with turbo + pnpm ready  
**Documentation**: Professional project foundation complete  
**Status**: Ready for implementation Phase 1

### Project Structure Context
```
v2/
├── services/
│   ├── orchestrator/        # 🎯 YOUR TARGET - LLM routing service
│   ├── guardian/           # ✅ EXISTS - System safety (Python FastAPI)
│   └── voice/              # ⏳ FUTURE - ASR/TTS pipeline
├── packages/
│   ├── api/                # 🎯 YOUR TARGET - TypeScript SDK
│   ├── types/              # 🎯 YOUR TARGET - Shared types
│   └── ui/                 # ⏳ FUTURE - Design system
└── apps/
    └── web/                # ⏳ FUTURE - Next.js frontend
```

## 🎯 Specific Implementation Requirements

### Owner: Backend Lead  
### Timeline: 3-4 days intensive development  
### Priority: P0 (Foundation Critical)

## 📐 Technical Specifications

### SLO Targets
- **API Response Time**: P95 <100ms for health/status endpoints
- **Contract Stability**: 100% backward compatibility guarantee
- **SDK Type Safety**: 100% TypeScript strict mode compliance
- **Integration Success**: 100% for basic HTTP requests

### Definition of Done Checklist
- [ ] **API Endpoints**: `/health`, `/api/orchestrator/ingest`, `/api/chat` functional
- [ ] **Structured Logging**: JSON format with trace IDs and correlation
- [ ] **SDK Integration**: TypeScript client communicating exclusively through APIs
- [ ] **OpenAPI Specification**: Auto-generated and version-controlled
- [ ] **Integration Tests**: Full test coverage for API contracts
- [ ] **Guardian Integration**: Orchestrator respects Guardian admission control
- [ ] **Error Handling**: Graceful degradation and meaningful error responses

## 🛠️ Implementation Architecture

### Orchestrator Service (Python FastAPI)
**Location**: `v2/services/orchestrator/`

**Core Responsibilities**:
1. **API Gateway**: Single entry point for all AI operations
2. **Model Router**: Route requests to appropriate LLM (Phase 1: always "micro")
3. **Guardian Integration**: Respect admission control (429/503 during protection)
4. **Request Lifecycle**: Logging, tracing, metrics collection
5. **Contract Stability**: Versioned APIs with backward compatibility

**Key Components**:
```python
# main.py - FastAPI application with middleware
# routers/chat.py - Chat completion endpoints
# routers/orchestrator.py - LLM routing logic
# services/guardian_client.py - Guardian system integration
# middleware/logging.py - Structured logging and tracing
# models/ - Pydantic request/response models
```

### TypeScript SDK (packages/api)
**Location**: `v2/packages/api/`

**Core Responsibilities**:
1. **HTTP Client**: Robust API communication with retry logic
2. **WebSocket Client**: Real-time communication (future voice integration)
3. **Type Safety**: Zod validation and TypeScript strict mode
4. **Error Handling**: Circuit breaker pattern and graceful failures
5. **Guardian Awareness**: Handle 429/503 responses appropriately

**Key Components**:
```typescript
// src/clients/orchestrator-client.ts - Main API client
// src/clients/guardian-client.ts - Guardian status client
// src/types/api.ts - Request/response type definitions
// src/utils/retry.ts - Retry logic and circuit breaker
// src/validation/ - Zod schemas for runtime validation
```

### Shared Types (packages/types)
**Location**: `v2/packages/types/`

**Core Responsibilities**:
1. **API Contracts**: Shared interfaces between services and clients
2. **Domain Models**: Core business logic types
3. **Version Management**: Versioned type definitions
4. **Validation Schemas**: Runtime type validation

## 🔧 Implementation Details

### Phase 1 Routing Strategy
**Keep It Simple**: Always route to "micro" model for now. Advanced routing comes in later phases.

```python
# Simple Phase 1 implementation
def route_request(request: IngestRequest) -> str:
    return "micro"  # Always return micro model for Phase 1
```

### API Payload Structure
**All requests must include versioning**:
```typescript
interface BaseRequest {
  v: "1";  // Version field for future compatibility
  session_id: string;
  timestamp?: number;
}

interface ChatRequest extends BaseRequest {
  message: string;
  model?: "auto" | "micro" | "planner" | "deep";
}
```

### Guardian Integration Example
```python
async def check_guardian_admission() -> bool:
    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.get("http://localhost:8787/guardian/health")
            guardian_state = response.json()
            
            # Block during emergency/lockdown states
            return guardian_state.get("state") not in ["EMERGENCY", "LOCKDOWN"]
    except:
        # Guardian down - proceed with caution (fail-open for Phase 1)
        return True
```

### Error Response Format
**Standardized error structure**:
```typescript
interface APIError {
  error: {
    code: string;
    message: string;
    details?: any;
    trace_id?: string;
    retry_after?: number; // For rate limiting
  };
}
```

## 📋 Step-by-Step Implementation Plan

### Day 1: Orchestrator Service Foundation
1. **Setup FastAPI Project Structure**
   ```bash
   cd v2/services/orchestrator
   python -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn pydantic httpx python-dotenv
   ```

2. **Create Core API Endpoints**
   - `/health` - Service health check
   - `/api/orchestrator/ingest` - Main ingestion endpoint (Phase 1 stub)
   - `/api/chat` - Chat completion endpoint

3. **Implement Guardian Integration**
   - Guardian health check client
   - Admission control middleware
   - 429/503 response handling

4. **Add Structured Logging**
   - JSON formatted logs
   - Trace ID correlation
   - Request/response logging

### Day 2: TypeScript SDK Development
1. **Setup Package Structure**
   ```bash
   cd v2/packages/api
   pnpm init
   pnpm add zod typescript @types/node
   pnpm add -D tsup
   ```

2. **Create HTTP Client**
   - Axios/fetch-based client with retry logic
   - Guardian-aware error handling
   - Circuit breaker pattern

3. **Add Type Definitions**
   - Request/response interfaces
   - Zod validation schemas
   - Error type definitions

### Day 3: Integration & Testing
1. **Create Integration Tests**
   - Orchestrator API endpoint tests
   - SDK client communication tests
   - Guardian integration scenarios
   - Error handling validation

2. **Performance Validation**
   - API response time testing
   - Concurrent request handling
   - Memory usage profiling

3. **Documentation**
   - OpenAPI spec generation
   - SDK usage examples
   - Integration guide

### Day 4: Polish & Production Readiness
1. **Error Handling Enhancement**
   - Comprehensive error scenarios
   - Graceful degradation
   - User-friendly error messages

2. **Monitoring Integration**
   - Metrics collection endpoints
   - Health check enhancements
   - Performance monitoring

3. **Final Testing**
   - End-to-end workflow validation
   - Load testing
   - Security review

## 🧪 Testing Strategy

### Unit Tests
```python
# Test orchestrator routing logic
def test_route_always_returns_micro():
    request = IngestRequest(v="1", session_id="test", text="hello")
    route = route_request(request)
    assert route == "micro"

# Test Guardian integration
async def test_guardian_admission_control():
    # Mock Guardian emergency state
    # Verify 503 response
    pass
```

### Integration Tests
```typescript
// Test SDK communication
describe('OrchestratorClient', () => {
  test('should handle successful chat request', async () => {
    const client = new OrchestratorClient({ baseURL: 'http://localhost:8000' });
    const response = await client.chat({
      v: "1",
      session_id: "test",
      message: "Hello Alice"
    });
    expect(response.response).toBeDefined();
  });
});
```

## 🎯 Success Metrics

### Technical Metrics
- **API Latency**: P95 <100ms ✅
- **Error Rate**: <1% for valid requests ✅  
- **Type Coverage**: 100% TypeScript strict mode ✅
- **Test Coverage**: >90% code coverage ✅

### Integration Metrics
- **Guardian Communication**: 100% success rate ✅
- **SDK Reliability**: Zero type errors in consuming code ✅
- **API Contract Stability**: No breaking changes ✅

## 🔍 Quality Gates

### Before Merge
- [ ] All unit tests pass (100%)
- [ ] Integration tests pass (100%)
- [ ] TypeScript compilation clean (0 errors)
- [ ] Python linting clean (ruff + mypy)
- [ ] Performance targets met (P95 <100ms)
- [ ] OpenAPI spec validates
- [ ] Guardian integration tested

### Production Readiness
- [ ] Load testing completed (50 concurrent users)
- [ ] Error handling validated
- [ ] Monitoring dashboards functional
- [ ] Documentation complete
- [ ] Security review passed

## 🚀 Next Steps After Completion

Upon successful completion of Step 1:
1. **Step 2**: Guardian gatekeeper integration will build upon this foundation
2. **Step 3**: Observability will instrument these APIs  
3. **Future Steps**: Voice service will communicate through this orchestrator
4. **Frontend**: Web application will use the TypeScript SDK exclusively

## 📚 Reference Documentation

- **ALICE_SYSTEM_BLUEPRINT.md**: Complete system architecture
- **ROADMAP.md**: Full 17-step implementation plan  
- **AGENTS.md**: Development environment and testing instructions
- **OPUS_IMPLEMENTATION_SPEC.md**: Detailed technical specifications

## 🎯 Final Success Criteria

**You will know Step 1 is complete when**:
1. `curl http://localhost:8000/health` returns 200 with service status
2. TypeScript SDK can successfully call all orchestrator endpoints
3. Guardian integration blocks requests during emergency states
4. All API responses include proper versioning (`"v":"1"`)
5. Structured logs show request tracing and correlation
6. Integration tests achieve 100% pass rate
7. Performance targets are met consistently

**Ready to build the foundation of Alice v2! 🚀**

---

*This is a complete, production-ready implementation specification. Execute systematically, test thoroughly, and build the robust foundation that all other Alice v2 components will depend upon.*