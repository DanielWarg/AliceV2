# Alice v2 Autonomous Testing System
*Real-data E2E testing with self-healing capabilities*

## Overview

The Alice v2 Testing System provides continuous, autonomous validation of the entire Alice AI Assistant stack using real Swedish voice data, actual tool integrations, and production-equivalent workloads. When issues are detected, the system automatically applies safe remediation or generates detailed issue reports for manual intervention.

## Key Features

- **Real Data Testing**: No mocks - uses actual Swedish Common Voice data, live RTSP streams, sandbox email/calendar accounts
- **Autonomous Remediation**: Automatically fixes common issues like VAD sensitivity, RAG context size, tool timeouts
- **Comprehensive SLO Monitoring**: Tracks 15+ performance metrics with P95 latency measurements
- **Chaos Engineering**: Network glitches, service failures, resource exhaustion simulation
- **Self-Healing**: Safe parameter adjustments within defined ranges with automatic rollback
- **Detailed Reporting**: Markdown summaries, CSV metrics, structured JSON logs

## Architecture

```
services/tester/
├── main.py                 # Test orchestrator & autonomous loop
├── scenarios.yaml          # Real E2E test scenarios (30+ tests)
├── config.py              # SLO targets and remediation ranges
├── runners/               # Component test execution
│   ├── voice_ws.py        # Real-time voice streaming tests
│   ├── nlu_eval.py        # Swedish intent classification
│   ├── planner_tools.py   # Live email/calendar integration
│   └── deep_eval.py       # Complex reasoning workloads
├── chaos/                 # Resilience testing
│   ├── network_glitch.py  # DNS timeouts, packet loss
│   └── service_failure.py # Controlled service outages
├── remedies/              # Self-healing actions
│   └── guardian_actions.py # Parameter tuning, cache clearing
└── metrics/               # Reporting and analysis
    └── writer.py          # Multi-format output generation
```

## Quick Start

### Prerequisites
- Alice v2 services running (orchestrator, guardian, voice)
- Docker and Docker Compose
- Sandbox accounts for email/calendar testing

### Run with Docker Compose
```bash
# Add to your docker-compose.yml
services:
  tester:
    build: ./services/tester
    depends_on: [orchestrator, guardian, voice, redis]
    environment:
      - API_BASE=http://orchestrator:8000
      - GUARDIAN_URL=http://guardian:8787
      - EMAIL_SMTP_URL=smtp://test:pass@sandbox-mail.example.com:587
      - CALDAV_URL=https://test:pass@sandbox-cal.example.com/caldav/
    volumes:
      - ./services/tester/runs:/runs
      - ./services/tester/datasources:/data

# Start testing
docker compose up -d tester

# View live results
tail -f services/tester/runs/latest/log.jsonl
```

### Run Locally
```bash
cd services/tester

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your service endpoints and sandbox credentials

# Run autonomous testing
python main.py
```

## Test Scenarios

### Voice Pipeline (Real Swedish Audio)
- **Clean Speech**: Common Voice Swedish clips, WER ≤7%
- **Noisy Environments**: Café, traffic, rain backgrounds, WER ≤11%
- **Real-time Streaming**: 20ms WebSocket chunks, partial <300ms
- **VAD Accuracy**: Voice activity detection precision/recall

### NLU & Intent Classification
- **Swedish Intent Recognition**: Regional dialects, colloquialisms
- **Slot Extraction**: Dates, times, names in Swedish context
- **Out-of-scope Detection**: Graceful handling of unknown requests

### LLM Integration (Real Tool Usage)
- **Email Operations**: Actual SMTP sending to sandbox accounts
- **Calendar Management**: Real CalDAV event creation/modification
- **Home Assistant**: Device control in development environment
- **Complex Reasoning**: Multi-step document analysis

### Chaos Engineering
- **Network Partitions**: DNS blackholing, connection timeouts
- **Service Failures**: Guardian emergency states, tool outages
- **Resource Exhaustion**: Memory pressure, CPU spikes
- **Recovery Testing**: Graceful degradation and failover

## SLO Targets

### Performance SLOs (P95)
| Metric | Target | Description |
|--------|--------|-------------|
| Voice E2E | ≤2000ms | Complete voice interaction |
| ASR Final | ≤800ms | Final transcript delivery |
| Planner First Token | ≤900ms | Planning LLM response start |
| Deep Reasoning | ≤1800ms | Complex analysis first token |
| Tool Success Rate | ≥95% | Email/calendar operations |
| Swedish WER Clean | ≤7% | Word error rate clean audio |
| Swedish WER Noisy | ≤11% | Word error rate with noise |

### System SLOs
- **Guardian Response**: ≤150ms state transitions
- **Memory Usage**: ≤15GB total system RAM
- **System Availability**: ≥99.5% uptime
- **Energy Efficiency**: Smart scheduling during low battery

## Autonomous Remediation

### Safe Actions (Automatic)
- **VAD Tuning**: Adjust sensitivity thresholds for noise handling
- **EOS Timeout**: Increase end-of-speech detection for better completion
- **RAG Optimization**: Reduce context window size for faster LLM processing
- **Cache Management**: Clear TTS cache, optimize memory usage
- **Tool Resilience**: Increase timeouts, enable circuit breakers
- **Guardian Tuning**: Adjust brownout thresholds within safety limits

### Safety Limits
- **Maximum 1 remediation per test cycle** (15 minutes)
- **All changes within pre-defined safe ranges**
- **Automatic rollback after 2 consecutive failures**
- **Manual intervention required signal after 3 failures**
- **No structural code changes** - only parameter adjustments

### Remediation Example
```
❌ Swedish WER degraded: 12.8% (target: ≤11%)
🔧 Remediation: Increased VAD end-of-speech timeout 700ms → 850ms
✅ Validation: Re-test shows 10.1% WER - FIXED
```

## Output Reports

### Run Summary (`runs/YYYYMMDD_HHMM/summary.md`)
- Overall pass/fail status with SLO compliance
- Performance metrics breakdown by component
- Remediation actions taken with reasoning
- Recommendations for manual improvements

### Detailed Metrics (`metrics.csv`)
- Per-scenario measurements for trending analysis
- P50/P95 latencies, error rates, resource usage
- Timestamp correlation for incident analysis

### Structured Logs (`log.jsonl`)
- Real-time event stream for monitoring
- Error details with stack traces
- Remediation action audit trail

### JSON Summary (`summary.json`)
- Programmatic access to results
- Integration with monitoring dashboards
- Historical trend analysis data

## Configuration

### Environment Variables
```bash
# Service endpoints
API_BASE=http://localhost:8000              # Alice orchestrator
GUARDIAN_URL=http://localhost:8787          # Guardian safety system
VOICE_SERVICE_URL=http://localhost:8001     # Voice pipeline

# SLO targets (milliseconds)
SLO_VOICE_E2E_MS=2000                       # End-to-end voice latency
SLO_ASR_FINAL_MS=800                        # ASR final transcript
SLO_PLANNER_FIRST_MS=900                    # Planner LLM first token

# Quality targets (ratios 0.0-1.0)
SLO_WER_CLEAN=0.07                          # Clean audio WER
SLO_WER_NOISY=0.11                          # Noisy audio WER
SLO_TOOL_SUCCESS_RATE=0.95                  # Tool operation success

# Sandbox credentials (never use production!)
EMAIL_SMTP_URL=smtp://test:pass@sandbox.example.com:587
CALDAV_URL=https://test:pass@cal-sandbox.example.com/caldav/
RTSP_URL=rtsp://demo:demo@test-cam.example.com/live.sdp

# Safety limits
REMEDIATION_ENABLED=true                     # Enable auto-remediation
MAX_REMEDIATIONS_PER_CYCLE=1                 # Limit remediation rate
REMEDIATION_COOLDOWN_S=1800                  # 30-minute cooldown
```

### Test Data Management
- **Swedish Voice Data**: Auto-downloads Common Voice dataset if missing
- **Background Noise**: Updates noise profiles weekly for realistic testing
- **Test Prompts**: Expands based on real user interactions from logs
- **Ground Truth**: Maintains transcription accuracy via human validation

## Monitoring & Alerts

### Dashboard Integration
The testing system outputs metrics compatible with:
- **Grafana**: Real-time SLO compliance dashboards
- **Prometheus**: Metrics scraping and alerting
- **Alice Dashboard**: Built-in performance visualization

### Alert Rules (Example)
```yaml
# High WER degradation
- alert: SwedishWERHigh
  expr: alice_test_wer > 0.11
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Swedish ASR accuracy degraded"

# Voice pipeline SLO violation  
- alert: VoicePipelineSlow
  expr: alice_test_voice_e2e_p95 > 2000
  for: 3m
  labels:
    severity: critical
```

## Development

### Adding New Test Scenarios
1. Add scenario to `scenarios.yaml`
2. Implement runner in appropriate `runners/` module
3. Define SLO targets and validation logic
4. Test locally before committing

### Custom Remediation Actions
1. Add handler to `remedies/guardian_actions.py`
2. Define safe parameter ranges in `config.py`
3. Implement rollback mechanism
4. Add tests for remediation logic

### Chaos Engineering
1. Create new chaos modules in `chaos/`
2. Implement controlled failure injection
3. Ensure graceful recovery validation
4. Document expected behaviors

## Security & Privacy

### Data Protection
- **Sandbox Only**: Never uses production credentials or user data
- **PII Masking**: Automatic detection and redaction in logs
- **Audio Retention**: Generated samples deleted after 24 hours
- **Consent Enforcement**: Respects memory write permissions

### Safe Remediation
- **No Code Changes**: Only parameter adjustments within ranges
- **Audit Trail**: All actions logged with rollback commands
- **Human Oversight**: Manual approval for structural changes
- **Blast Radius**: Changes isolated to test environment

---

**Alice v2 Autonomous Testing System ensures production quality through continuous, real-world validation with intelligent self-healing capabilities.**

🎯 **Ready to catch regressions before they reach users!**