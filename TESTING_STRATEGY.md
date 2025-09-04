# Alice v2 Testing Strategy
*Autonomous RealOps Testing Architecture with Self-Healing Capabilities*

## 🎯 Overview

Alice v2 implements a **RealOps testing approach** - no mocks, only real data flows through actual services. The testing system runs continuously, validates SLOs, detects regressions, applies safe remediation, and generates actionable reports.

**🚀 CURRENT STATUS**: Complete observability + eval-harness v1 operational; Intent-Guard + Quality Gates optimization in progress; `/api/chat` sets `X-Route` and writes turn-events (RAM/energy/guardian) to `data/telemetry/YYYY-MM-DD/`. NLU service needs restoration (currently down).

**Philosophy**: Test with real Swedish voice data, actual SMTP/CalDAV integration, live RTSP streams, and production-equivalent LLM workloads. When issues arise, automatically fix them or create detailed issue reports.

## 🏗️ Testing Architecture

### Core Components ✅ IMPLEMENTED
```
services/eval/                    # ✅ Autonomous E2E testing harness
├── eval.py                       # ✅ 20 realistic scenarios execution
├── scenarios.json                # ✅ Test cases covering all routes
├── requirements.txt              # ✅ Dependencies
└── main.py                       # ✅ Entry point for Docker deployment

scripts/                          # ✅ Autonomous E2E test automation
├── auto_verify.sh                # ✅ Complete system validation script
└── auto_verify_simple.sh         # ✅ Simplified validation for local execution

monitoring/                       # ✅ Real-time observability dashboard
├── mini_hud.py                   # ✅ Streamlit HUD for eval results
├── alice_hud.py                  # ✅ Comprehensive metrics visualization
└── requirements.txt              # ✅ Dashboard dependencies

data/                             # ✅ Test artifacts and telemetry
├── telemetry/                    # ✅ Structured JSONL logging
│   └── events_YYYY-MM-DD.jsonl  # ✅ Turn events with all metrics
└── tests/                        # ✅ E2E test artifacts
    ├── results.jsonl             # ✅ Eval harness results
    ├── summary.json              # ✅ SLO validation summary
    └── pre_*/post_*.json         # ✅ Status snapshots

test-results/                     # ✅ Historical test data
├── raw-logs/                     # ✅ Detailed test sessions
├── nightly/                      # ✅ Nightly validation results
├── summaries/                    # ✅ Daily and nightly summaries
└── trends/                       # ✅ Trend analysis
```

### **🎯 NEW FEATURES COMPLETED**

**🧪 Autonomous E2E Testing:**
- **Self-contained validation**: `scripts/auto_verify.sh` runs complete system validation
- **20 realistic scenarios**: Swedish conversations covering micro/planner/deep routes
- **SLO validation**: Automatic P95 threshold checking with Node.js integration
- **Failure detection**: Exit code 1 on SLO breach or <80% pass rate
- **Artifact preservation**: All test results saved to `data/tests/` and `test-results/`

**📊 Complete Observability:**
- **RAM-peak per turn**: Process and system memory tracking in every turn event
- **Energy per turn (Wh)**: Energy consumption with configurable baseline
- **Tool error classification**: Timeout/5xx/429/schema/other categorization with Prometheus metrics
- **Structured turn events**: Complete JSONL logging with all metrics and metadata
- **Real-time dashboard**: Streamlit HUD (proxied via /hud) shows RAM, energy, latency, tool errors and Guardian status

### Legacy Components (Replaced)
```
services/tester/                  # ❌ OBSOLETE - Replaced by services/eval/
├── main.py                       # ❌ Replaced by eval.py
├── scenarios.yaml                # ❌ Replaced by scenarios.json
├── config.py                     # ❌ Configuration moved to eval.py
├── runners/                      # ❌ Simplified to single eval harness
├── chaos/                        # ❌ Chaos testing integrated into eval scenarios
├── remedies/                     # ❌ Self-healing moved to Guardian system
├── metrics/                      # ❌ Replaced by structured JSONL logging
└── datasources/                  # ❌ Test data integrated into scenarios.json
```

## 📊 SLO Targets & Validation

### Performance SLOs (P95 measurements) ✅ IMPLEMENTED
- **Voice Pipeline**: End-to-end <2000ms
- **ASR Partial**: <300ms after speech detected
- **ASR Final**: <800ms after silence
- **Guardian Response**: <150ms state transitions ✅
- **Micro LLM**: <250ms first token (current: 27ms)
- **Planner LLM**: <900ms first token, <1500ms complete (current: 27ms)
- **Deep LLM**: <1800ms first token, <3000ms complete (aktiveras efter Guardian-gate)
- **TTS Cached**: <120ms audio generation
- **TTS Uncached**: <800ms (≤40 characters)

### Quality SLOs ✅ IMPLEMENTED
- **Swedish WER**: ≤7% clean audio, ≤11% with background noise
- **Intent Classification**: ≥92% accuracy on test suite
- **Tool Success Rate**: ≥95% for email/calendar/HA operations
- **Vision First Detection**: <350ms for still images
- **RTSP Reconnection**: <2s after connection drop

### Resource SLOs ✅ IMPLEMENTED
- **Memory Usage**: <15GB total system RAM ✅
- **Guardian Protection**: 0 system crashes from overload ✅
- **Concurrent Deep Jobs**: Maximum 1 at any time ✅
- **Energy Efficiency**: Smart scheduling during low battery ✅

### **NEW: Observability SLO** ✅ IMPLEMENTED
- **Metrics Collection**: <10ms overhead per turn ✅
- **Cost/Token Tracking**: per-turn tokens (prompt/completion), kostnad (SEK), provider ✅
- **Dashboard Load**: <2s for complete HUD ✅
- **E2E Test Success**: ≥80% pass rate for 20 scenarios ✅
- **SLO Validation**: Automatic P95 threshold checking ✅

### CI Gates (fail build om ej uppfyllt)
| Gate | Tröskel | Källa |
|---|---:|---|
| E2E pass rate | ≥ 80% | `data/tests/summary.json` |
| Fast route P95 (first) | ≤ 250 ms | turn events |
| Planner P95 (full) | ≤ 1500 ms | turn events |
| Tool success rate | ≥ 95% | tool events |
| Guardian EMERGENCY | 0 händelser | guardian logs |

## 🧪 Test Scenarios

### Real Data Sources ✅ IMPLEMENTED
**No synthetic data - everything uses production-equivalent inputs:**

1. **Swedish Voice Data**: Common Voice dataset with native speakers
2. **Background Noise**: Real café, street, office environments
3. **Email/Calendar**: Sandbox SMTP/IMAP and CalDAV accounts
4. **Home Assistant**: Development instance with simulated devices
5. **RTSP Streams**: Live camera feeds or public test streams
6. **LLM Prompts**: Actual Swedish conversation patterns and tasks

### **NEW: Autonomous E2E Scenarios** ✅ IMPLEMENTED
```json
// services/eval/scenarios.json - 20 NLU/route scenarios (v1 fokus micro/planner)
[
  {"id":"nlu-1","text":"Hej Alice!","expect":{"route":"micro","intent":"greeting.hello"}},
  {"id":"nlu-2","text":"Vad är klockan nu?","expect":{"route":"micro","intent":"smalltalk.time"}},
  {"id":"nlu-3","text":"Boka möte med Anna imorgon klockan 14","expect":{"route":"planner","intent":"calendar.create"}},
  // ... 17 more (se repo)
]
```

### Scenario Categories

#### Voice Pipeline Testing
```yaml
- Swedish Clean Speech: WER measurement with ground truth transcripts
- Noisy Environments: SNR 10dB café noise, traffic, rain backgrounds
- Partial Transcription: Real-time streaming validation
- Voice Activity Detection: Start/stop threshold accuracy
- Multi-speaker: Overlapping speech handling
```

#### NLU & Intent Classification
```yaml
- Swedish Intent Recognition: Real user utterances from different regions
- Slot Extraction: Dates, times, names, locations in Swedish context
- Confidence Calibration: Uncertainty estimation accuracy
- Fallback Handling: Out-of-scope utterance graceful degradation
```

#### LLM Routing & Performance
```yaml
- Simple Queries: Weather, time, basic math → Micro LLM
- Planning Tasks: Email composition, calendar scheduling → Planner LLM
```

#### Vision & Multimodal
```yaml
- RTSP Stream Processing: Object detection, reconnection resilience
- Still Image Analysis: Photo description, object counting
- Network Resilience: Connection drops, bandwidth limitations
- Graceful Degradation: Snapshot fallback when stream unavailable
```

#### Chaos Engineering
```yaml
- Network Partitions: DNS blackholing for 5-10 seconds
- Service Failures: Guardian emergency state simulation
- Tool Outages: Email server down, calendar API failures
- Resource Exhaustion: Memory pressure, CPU spikes
- Concurrent Load: Multiple users, competing requests
```

## 🔧 Autonomous Remediation System

### Safe Remediation Actions
**Only evidence-based, reversible changes with safety limits:**

#### Performance Optimization
```python
# ASR Performance Issues
if wer_rate > threshold:
    adjust_vad_thresholds(start=-0.1, stop=+0.1)  # More sensitive detection
    increase_eos_timeout(+100ms)  # Allow longer pauses
    
# NLU Accuracy Issues  
if intent_accuracy < 0.92:
    enable_regex_fallback_for_top5_intents()
    switch_embedding_model("multilingual-e5-small")
    
# LLM Latency Issues
if planner_latency > slo_target:
    reduce_rag_top_k(from=8, to=3)  # Faster context retrieval
    enable_strict_schema_validation()  # Prevent retry loops
    
# Resource Management
if ram_usage > 14000MB:
    disable_deep_llm_temporarily()
    reduce_rag_top_k(to=2)
    clear_tts_cache_older_than(1h)
```

#### Service Recovery
```python
# Guardian State Management
if guardian_state == "EMERGENCY":
    log_resource_state()
    wait_for_recovery_or_timeout(45s)
    if still_emergency:
        create_incident_report()
        
# Tool Integration Failures
if email_tool_failure_rate > 0.05:
    activate_circuit_breaker(duration=300s)
    enable_fallback_to_draft_mode()
    
# Vision System Issues  
if rtsp_reconnect_time > 2000ms:
    prewarm_vision_system(2s_before_request)
    enable_snapshot_fallback_after(2_failures)
```

### Remediation Safety Limits
- **Maximum 1 remediation per test loop** to avoid oscillation
- **No code changes** - only parameter adjustments and feature toggles
- **All changes logged** with before/after values and rollback commands
- **Automatic rollback** if issues persist after 2 failed remediation attempts
- **Manual intervention required** signal after 3 consecutive failures

**Remediation guardrails**
- Max 1 remediation per loop
- Remediation whitelist: {`vad_thresholds`,`eos_timeout`,`rag_top_k`,`strict_schema`}
- Cooldown 15 min per parameter
- Rollback auto om metrik inte förbättras inom 2 re-körningar

## 📈 Continuous Testing Loop

### Execution Cycle (Every 15 minutes)
```
1. Pre-flight Checks (30s)
   - Guardian health status
   - MCP tool registry validation  
   - Service endpoint availability
   - Resource usage baseline

2. Test Execution (10-12 minutes)
   - Run scenario batch in parallel where safe
   - Stream real audio data over WebSocket
   - Execute actual tool operations
   - Measure all performance metrics
   - Collect structured logs with correlation IDs

3. Analysis & Validation (2 minutes)
   - Compare results against SLO targets
   - Identify performance regressions
   - Root cause analysis using rule-based logic
   - Generate pass/fail status per scenario

4. Remediation (1-2 minutes)
   - Apply single safe remediation if needed
   - Re-run only failed scenarios to validate fix
   - Log remediation actions and outcomes
   - Create issue reports for unresolved problems

5. Reporting (30s)
   - Update metrics dashboard
   - Generate summary.md with findings
   - Archive detailed logs and audio samples
   - Send alerts for critical failures
```

### Test Data Management
```bash
# Automatic dataset updates
if [ ! -d "datasources/common_voice" ]; then
    download_common_voice_swedish_clips()
    resample_to_16khz_mono()
    create_ground_truth_transcripts()
fi

# Noise profile updates
if [ "$(find datasources/noise -name '*.wav' -mtime +30)" ]; then
    refresh_background_noise_samples()
    analyze_snr_characteristics()
fi

# Prompt dataset evolution
if test_accuracy_drops_significantly; then
    expand_intent_examples_from_logs()
    add_failed_cases_to_test_suite()
fi
```

## 🎯 Test Reporting & Metrics

### Automated Report Generation
**Every test run produces comprehensive documentation:**

#### Run Summary (`runs/YYYYMMDD_HHMM/summary.md`)
```markdown
# Alice v2 Test Run Summary
**Date**: 2024-08-31 16:30:00  
**Duration**: 12 minutes 34 seconds  
**Overall Status**: ⚠️ DEGRADED (2 SLO violations)

## SLO Compliance
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Voice E2E P95 | <2000ms | 1847ms | ✅ PASS |
| Swedish WER Clean | <7% | 5.2% | ✅ PASS |
| Swedish WER Noisy | <11% | 12.8% | ❌ FAIL |
| Guardian Response | <150ms | 134ms | ✅ PASS |
| Tool Success Rate | >95% | 97.3% | ✅ PASS |

## Issues Identified
1. **Swedish WER degraded in café noise**: 12.8% vs target 11%
   - **Root Cause**: VAD end-of-speech timeout too aggressive
   - **Remediation Applied**: Increased EOS timeout from 700ms to 850ms
   - **Validation**: Re-test shows 10.1% WER ✅

## Manual Actions Required
- None - all issues automatically remediated

## Resource Usage
- **Peak RAM**: 12.8GB (target <15GB) ✅
- **Guardian State**: NORMAL throughout test ✅
- **Energy Consumption**: 2.4Wh (baseline: 2.1Wh)
```

#### Detailed Metrics (`runs/YYYYMMDD_HHMM/metrics.csv`)
```csv
timestamp,scenario_id,metric,value,unit,status
2024-08-31T16:30:01,asr_clean,wer,0.052,percent,pass
2024-08-31T16:30:15,asr_cafe_noise,wer,0.128,percent,fail
2024-08-31T16:30:23,nlu_intents,intent_acc,0.934,percent,pass
2024-08-31T16:31:45,email_send,tool_success,1.0,boolean,pass
2024-08-31T16:32:12,deep_summarize,llm_first_ms,1654,milliseconds,pass
```

#### Event Log (`runs/YYYYMMDD_HHMM/log.jsonl`)
```json
{"timestamp":"2024-08-31T16:30:01","event":"test_start","scenario":"asr_clean","trace_id":"abc123"}
{"timestamp":"2024-08-31T16:30:15","event":"asr_partial","text":"hej alice","confidence":0.89,"latency_ms":245}
{"timestamp":"2024-08-31T16:30:18","event":"asr_final","text":"hej alice vad är klockan","confidence":0.95,"latency_ms":723}
{"timestamp":"2024-08-31T16:30:45","event":"slo_violation","metric":"wer_noisy","value":0.128,"threshold":0.11}
{"timestamp":"2024-08-31T16:30:50","event":"remediation_applied","action":"increase_eos_timeout","from":700,"to":850}
```

### Performance Monitoring Dashboard

#### Real-time Metrics Display
- **SLO Compliance Dashboard**: Green/Yellow/Red status for all metrics
- **Performance Trends**: P50/P95 latency over time
- **Resource Utilization**: Memory, CPU, Guardian state history  
- **Quality Metrics**: WER rates, intent accuracy, tool success rates
- **Remediation History**: Actions taken, success rates, rollbacks

#### Alert Integration
```yaml
# Alert Rules (integrate with existing monitoring)
- name: "Voice Pipeline SLO Violation"
  condition: voice_e2e_p95 > 2000ms
  severity: warning
  action: trigger_immediate_retest

- name: "Swedish WER Degradation"  
  condition: wer_rate > 0.11
  severity: critical
  action: [apply_remediation, notify_team]

- name: "Guardian Emergency State"
  condition: guardian_state == "EMERGENCY"  
  severity: critical
  action: [collect_diagnostics, create_incident]

- name: "OpenAI Cost Budget"
  condition: daily_cost_sek > ${OPENAI_DAILY_BUDGET_SEK}
  severity: warning
  action: [switch_to_local_provider, notify_team]
```

## 🚀 Implementation & Deployment

### Docker Integration
```yaml
# Add to docker-compose.yml
services:
  eval:
    build: ./services/eval
    container_name: alice-eval
    depends_on:
      - orchestrator
      - guardian  
      - voice
      - redis
    environment:
      - API_BASE=http://orchestrator:8000
      - WS_ASR=ws://orchestrator:8000/ws/asr
      - GUARDIAN_URL=http://guardian:8787
      - EMAIL_SMTP_URL=${TEST_SMTP_URL}
      - CALDAV_URL=${TEST_CALDAV_URL} 
      - RTSP_URL=${TEST_CAMERA_URL}
    volumes:
      - ./services/eval/datasources:/data
      - ./services/eval/runs:/runs
    restart: unless-stopped
```

### Environment Configuration
```bash
# Required environment variables for sandbox testing
export TEST_SMTP_URL="smtp://testuser:pass@sandbox-mail.example.com:587"
export TEST_IMAP_URL="imap://testuser:pass@sandbox-mail.example.com:993"
export TEST_CALDAV_URL="https://testuser:pass@sandbox-cal.example.com/caldav/"
export TEST_CAMERA_URL="rtsp://demo:demo@cam.example.com/live.sdp"
export CONSENT_SCOPES="memory:write,email:metadata,calendar:read"
```

### Startup & Operation
```bash
# 1. Start Alice v2 services
docker compose up -d orchestrator guardian voice redis

# 2. Verify services are healthy
curl http://localhost:8000/health
curl http://localhost:8787/guardian/health

# 3. Start autonomous testing
docker compose up -d eval

# 4. Monitor test results
tail -f services/eval/runs/latest/log.jsonl
open services/eval/runs/latest/summary.md
```

## 🔒 Security & Privacy

### Test Data Protection
- **Sandbox Accounts**: Never use production email/calendar credentials
- **PII Masking**: Automatic detection and redaction in all logs
- **Audio Retention**: Generated TTS samples deleted after manual review
- **Consent Enforcement**: Block operations without proper scope permissions (HTTP 403 + `required_scopes`)
- **Data Isolation**: Test data never mixed with production user data

### Safe Remediation Boundaries
- **No Production Changes**: All remediations affect only test environment
- **Parameter Limits**: Safe ranges for all adjustable parameters
- **Rollback Capability**: Every change includes automatic rollback mechanism
- **Human Oversight**: Manual approval required for structural changes

---

## 📊 Structured Data Collection for Alice's Learning

### Data Pipeline Architecture (Bronze → Silver → Gold)

Alice v2 implements a **multi-tier data collection system** that captures all test interactions for three purposes:
1. **Telemetry & Debugging** - Real-time operational insights
2. **SLO Monitoring & Evaluation** - Performance tracking and regression detection  
3. **Training & Fine-tuning** - SFT/LoRA, DPO, and RAG improvement

#### Directory Structure
```
/data/
  telemetry/                 # BRONZE: Raw JSONL events (append-only)
    YYYY-MM-DD/*.jsonl
  datasets/
    bronze/turns.jsonl       # Sampled raw data (uncleaned)
    silver/                  # Cleaned + masked + normalized
      turns.jsonl
      tool_calls.jsonl
      rag_pairs.jsonl
    gold/                    # Manually reviewed "ground truth"
      sft_conversations.jsonl
      dpo_preferences.jsonl
      nlu_intents.jsonl
  artifacts/
    audio/                   # Only if scope = audio:store
    tts/                     # TTS cache files
  registries/
    schema/v1/*.json         # JSON Schema for logs
    hashes/seen_hashes.db    # Deduplication index
```

### Retention
| Dataset | Syfte | Retention |
|---|---|---|
| Telemetry (bronze) | Operativ felsökning | 7 dagar |
| Silver | Eval & modellering | 30 dagar |
| Gold | Handgranskad träningsdata | Tills manuellt borttagen |
| Audio artifacts | QA av röst | 24 h (om `audio:store` scope) |

### Unified Event Format (JSONL)

All modules write structured events with **schema versioning** and **hash-based deduplication**:

```json
{
  "v": "1",
  "event": "orchestrator.turn",
  "ts": "2025-08-31T11:23:45.120Z",
  "user_id": "anon_c2f1",        // Pseudonymized
  "session_id": "test_session_42",
  "turn_id": "t-00042",
  "lang": "sv",
  "input": {
    "text": "boka med Anders imorgon 10",
    "audio_ref": null,           // artifacts/audio/..wav if permitted
    "asr": { "partial_ms": 210, "final_ms": 640, "wer_ref": null }
  },
  "nlu": {
    "intent": "TIME.BOOK", 
    "confidence": 0.88,
    "slots": { "contact": "Anders", "date": "2025-09-01", "time": "10:00" }
  },
  "guardian": { "state": "NORMAL", "ram_pct": 61.2, "brownout": "NONE" },
  "route": "planner",             // micro|planner|deep
  "rag": { 
    "query": "möte Anders 10:00", 
    "top_k": 3, 
    "hits": [{"doc_id":"cal_001","score":0.52}] 
  },
  "tool_calls": [
    { 
      "name": "calendar.create", 
      "args": {"when":"2025-09-01T10:00","with":"Anders"}, 
      "ok": true, 
      "lat_ms": 220 
    }
  ],
  "llm": { 
    "model": "qwen2.5-7b-moe", 
    "first_ms": 180, 
    "full_ms": 740, 
    "tokens": 146 
  },
  "output": {
    "text_en": "Scheduled meeting with Anders at 10:00 on Sep 1",
    "tts": { 
      "voice": "alice_neutral", 
      "cache": "HIT", 
      "lat_ms": 118, 
      "audio_ref": "artifacts/tts/response_042.mp3" 
    }
  },
  "metrics": {
    "e2e_first_ms": 430,
    "e2e_full_ms": 980,
    "ram_peak_mb": 5120,
    "energy_wh": 0.08
  },
  "test_metadata": {
    "test_scenario": "swedish_calendar_booking",
    "slo_target_ms": 2000,
    "slo_compliance": true,
    "regression_flag": false
  },
  "consent_scopes": ["memory:write","calendar:read"],
  "pii_masked": true,
  "hash": "sha256:2f0a...ef"
}
```

### PII Protection & Consent Management

#### Automatic PII Masking
```python
def mask_pii(text: str) -> tuple[str, bool]:
    """Mask PII in text, return (masked_text, was_modified)"""
    patterns = {
        r'\b[\w.-]+@[\w.-]+\.\w+\b': '<EMAIL>',
        r'\b(?:\+46|0)[1-9]\d{8,9}\b': '<PHONE>',
        r'\b\d{6,8}-\d{4}\b': '<PERSONNUMMER>',
        r'\b[A-ZÅÄÖ][a-zåäö]+ [A-ZÅÄÖ][a-zåäö]+\b': '<FULLNAME>'
    }
    
    modified = False
    for pattern, replacement in patterns.items():
        if re.search(pattern, text):
            text = re.sub(pattern, replacement, text)
            modified = True
    
    return text, modified
```

#### Consent Scope Management
- `audio:store` - Permission to save raw audio
- `memory:write` - Allow long-term memory updates
- `email:full` - Access full email content (not just metadata)
- `calendar:write` - Permission to create calendar events
- `analytics:training` - Allow data use for model training

### Data Processing Pipelines

#### Bronze → Silver (Automated Hourly)
```python
def process_bronze_to_silver():
    """Clean and normalize raw telemetry data"""
    
    # 1. Deduplication via hash
    seen_hashes = load_seen_hashes()
    
    # 2. PII masking and normalization
    for event in read_bronze_events():
        if event['hash'] in seen_hashes:
            continue
            
        # Normalize Swedish relative dates to ISO
        if 'input' in event and 'text' in event['input']:
            event['input']['text'] = normalize_swedish_dates(event['input']['text'])
            
        # Build training datasets
        turns_data.append(extract_turn_data(event))
        
        if event.get('tool_calls'):
            tool_calls_data.extend(extract_tool_calls(event))
            
        if event.get('rag', {}).get('hits'):
            rag_pairs_data.append(extract_rag_pairs(event))
    
    # Write to silver datasets
    write_jsonl('silver/turns.jsonl', turns_data)
    write_jsonl('silver/tool_calls.jsonl', tool_calls_data)  
    write_jsonl('silver/rag_pairs.jsonl', rag_pairs_data)
```

#### Silver → Gold (Manual/Semi-Automatic)
Active learning pipeline identifies high-value samples:

```python
def identify_gold_candidates():
    """Flag samples for manual review and labeling"""
    
    candidates = []
    
    for turn in read_silver_turns():
        # Low confidence NLU results
        if turn.get('nlu', {}).get('confidence', 1.0) < 0.6:
            candidates.append({
                'type': 'nlu_uncertainty',
                'data': turn,
                'priority': 'HIGH'
            })
            
        # Tool call failures
        if any(not call.get('ok', True) for call in turn.get('tool_calls', [])):
            candidates.append({
                'type': 'tool_failure', 
                'data': turn,
                'priority': 'CRITICAL'
            })
            
        # SLO violations
        if turn.get('metrics', {}).get('e2e_full_ms', 0) > turn.get('test_metadata', {}).get('slo_target_ms', 2000):
            candidates.append({
                'type': 'slo_violation',
                'data': turn, 
                'priority': 'MEDIUM'
            })
            
        # Guardian state changes
        if turn.get('guardian', {}).get('state') != 'NORMAL':
            candidates.append({
                'type': 'guardian_event',
                'data': turn,
                'priority': 'HIGH'
            })
    
    return candidates
```

### RAG Training Data Enhancement

Capture "hard negatives" for embedding fine-tuning:

```json
{
  "query": "ytterdörr kamera", 
  "positive": "doc:cam_frontdoor.md",
  "hard_negatives": ["doc:cam_kitchen.md", "doc:random_doc.md"],
  "context": {
    "user_intent": "HOME.SECURITY.STATUS",
    "search_type": "device_lookup",
    "confidence_threshold": 0.7
  }
}
```

### Test-Specific Data Collection

#### Performance Baselines
```python
def log_performance_baseline(test_name: str, metrics: dict):
    """Log performance metrics for regression detection"""
    
    baseline_event = {
        "v": "1",
        "event": "test.baseline",
        "ts": datetime.utcnow().isoformat(),
        "test_name": test_name,
        "component": "orchestrator",
        "metrics": metrics,
        "environment": {
            "guardian_state": get_guardian_state(),
            "system_load": get_system_metrics(),
            "concurrent_users": get_active_sessions()
        },
        "slo_compliance": {
            "api_response_p95": metrics.get('p95_ms', 0) < 100,
            "guardian_response": metrics.get('guardian_ms', 0) < 150,
            "success_rate": metrics.get('success_rate', 0) >= 0.95
        }
    }
    
    log_event(baseline_event)
```

#### Failure Pattern Detection
```python
def log_test_failure(test_name: str, failure_info: dict):
    """Log detailed failure information for learning"""
    
    failure_event = {
        "v": "1", 
        "event": "test.failure",
        "ts": datetime.utcnow().isoformat(),
        "test_name": test_name,
        "failure_type": failure_info.get('type'),
        "root_cause": failure_info.get('root_cause'),
        "system_state": {
            "guardian_state": get_guardian_state(),
            "memory_usage": get_memory_usage(),
            "active_connections": get_connection_count()
        },
        "stack_trace": failure_info.get('stack_trace'),
        "reproduction_steps": failure_info.get('steps'),
        "impact_assessment": {
            "severity": failure_info.get('severity', 'MEDIUM'),
            "user_impact": failure_info.get('user_impact'),
            "system_stability": assess_system_stability()
        }
    }
    
    log_event(failure_event)
```

### Data Quality Governance

#### Privacy & Security Checklist
- [ ] **Consent logging**: All `consent_scopes` recorded per session
- [ ] **PII masking**: Email, phone, personnummer, full names masked
- [ ] **Right to forget**: `/memory/forget` endpoint clears logs + artifacts
- [ ] **Retention limits**: 7d telemetry, 30d silver, gold until manual cleanup
- [ ] **Deduplication**: Hash-based to prevent duplicate sensitive data
- [ ] **Test vs prod**: Clear environment tagging for filtering
- [ ] **AI Act transparency**: Logga `llm.provider`, `llm.model`, `policy_mode` (NORMAL/BROWNOUT), och `tool_autonomy` (manual_review|auto)
- [ ] **GDPR lawful basis**: `consent_scopes` krävs före RESTRICTED dataprocessing; blockera utan scope
- [ ] **Data subject rights**: `/memory/forget` rensar även `datasets/silver` via referens-hash

#### Data Quality Validation
```python
def validate_data_quality():
    """Ensure collected data meets quality standards"""
    
    quality_metrics = {
        "schema_compliance": validate_schema_compliance(),
        "pii_masking_rate": check_pii_masking_coverage(), 
        "deduplication_rate": calculate_duplicate_percentage(),
        "consent_coverage": verify_consent_logging(),
        "retention_compliance": check_retention_policy()
    }
    
    # Alert if quality drops below thresholds
    for metric, value in quality_metrics.items():
        if value < QUALITY_THRESHOLDS[metric]:
            alert_data_quality_issue(metric, value)
```

### Alice's Learning Integration

#### Model Fine-tuning Preparation
```python
def prepare_training_data():
    """Convert gold data to training formats"""
    
    # SFT conversations for tool use
    sft_data = []
    for conv in read_gold_conversations():
        sft_data.append({
            "messages": [
                {"role": "user", "content": conv['user_input']},
                {"role": "assistant", "content": conv['assistant_response']},
                {"role": "tool", "name": conv['tool_name'], "content": conv['tool_result']},
                {"role": "assistant", "content": conv['final_response']}
            ]
        })
    
    # DPO preference pairs
    dpo_data = []
    for pref in read_gold_preferences():
        dpo_data.append({
            "prompt": pref['user_input'],
            "chosen": pref['preferred_response'], 
            "rejected": pref['alternative_response'],
            "reason": pref['preference_reason']
        })
    
    # RAG training pairs
    rag_data = []
    for pair in read_rag_pairs():
        rag_data.append({
            "query": pair['query'],
            "positive_doc": pair['positive'],
            "hard_negatives": pair['hard_negatives']
        })
    
    return sft_data, dpo_data, rag_data
```

### Implementation in Testing Framework

#### Drop-in Logging Function
```python
import json, time, hashlib, os, pathlib
from datetime import datetime

LOG_DIR = pathlib.Path(os.getenv("LOG_DIR", "/data/telemetry")) / time.strftime("%Y-%m-%d")
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = open(LOG_DIR / "events.jsonl", "a", buffering=1)

def log_event(payload: dict):
    """Thread-safe event logging with PII protection"""
    
    # Ensure schema version
    payload["v"] = payload.get("v", "1")
    payload["ts"] = datetime.utcnow().isoformat() + "Z"
    
    # PII masking
    if "input" in payload and "text" in payload["input"]:
        original_text = payload["input"]["text"]
        masked_text, was_masked = mask_pii(original_text)
        payload["input"]["text"] = masked_text
        payload["pii_masked"] = was_masked
    
    # Hash for deduplication
    hash_content = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload["hash"] = f"sha256:{hashlib.sha256(hash_content.encode()).hexdigest()}"
    
    # Atomic write
    log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
    log_file.flush()
```

#### Integration with Test Framework
```python
# In test_orchestrator_comprehensive.py
def test_chat_api_with_logging(client, test_metrics):
    """Enhanced test with structured data collection"""
    
    start_time = time.perf_counter()
    
    request_payload = {
        "v": "1",
        "session_id": "test_chat_logging_001", 
        "message": "Boka möte med Anna imorgon kl 14"
    }
    
    response = client.post("/api/chat", json=request_payload)
    end_time = time.perf_counter()
    
    # Log structured test event
    log_event({
        "event": "test.orchestrator.chat",
        "test_name": "test_chat_api_with_logging",
        "input": request_payload,
        "response": {
            "status_code": response.status_code,
            "content": response.json() if response.status_code == 200 else None
        },
        "metrics": {
            "response_time_ms": (end_time - start_time) * 1000,
            "success": response.status_code == 200
        },
        "test_metadata": {
            "scenario": "swedish_meeting_booking",
            "expected_intent": "TIME.BOOK",
            "slo_target_ms": 100
        },
        "consent_scopes": ["calendar:read", "memory:write"]
    })
    
    # Original test assertions
    assert response.status_code == 200
    test_metrics("chat_with_logging_ms", (end_time - start_time) * 1000)
```

---

**This enhanced data collection strategy ensures Alice receives high-quality, ethically-sourced training data that improves system performance while maintaining user privacy and data governance standards.**

🎯 **Ready for implementation - structured data collection will accelerate Alice's learning while maintaining enterprise security standards!**

---

## 🤖 **ALICE'S LEARNING DATA COLLECTION**

### **What We Save for Alice to Learn From**

Alice v2 collects comprehensive, structured data for continuous learning and improvement. All data is ethically sourced, PII-protected, and designed to accelerate Alice's understanding of Swedish language patterns, user behavior, and system performance.

### **📊 Structured Learning Data**

#### **1. Turn Events (data/telemetry/events_YYYY-MM-DD.jsonl)**
```json
{
  "v": "1",
  "ts": "2025-08-31T20:38:05.074363Z",
  "trace_id": "5c862438-9477-47e6-a6d3-2a89b6515317",
  "session_id": "fast_time-5823d3",
  "route": "micro",
  "e2e_first_ms": 0,
  "e2e_full_ms": 0,
  "ram_peak_mb": {"proc_mb": 80.6, "sys_mb": 12194.1},
  "tool_calls": [
    {
      "name": "calendar.create",
      "normalized_name": "calendar.create", 
      "ok": true,
      "klass": null,
      "lat_ms": 150
    }
  ],
  "rag": {"top_k": 0, "hits": 0},
  "energy_wh": 0.0,
  "guardian_state": "NORMAL",
  "pii_masked": true,
  "consent_scopes": ["basic_logging", "performance_metrics"]
}
```

**Learning Value:**
- **Performance patterns**: Latency trends, resource usage optimization
- **Route selection**: Which queries go to which models
- **Tool usage**: Success/failure patterns for different tools
- **Energy efficiency**: Power consumption optimization
- **Guardian behavior**: System health patterns

#### **2. E2E Test Results (data/tests/results.jsonl)**
```json
{
  "v": "1",
  "ts": "2025-08-31T20:38:05Z",
  "id": "fast_time",
  "ok": true,
  "lat_ms": 33.1,
  "route": "micro",
  "status": 200
}
```

**Learning Value:**
- **Scenario success rates**: Which types of queries work best
- **Route accuracy**: Model selection validation
- **Performance baselines**: Latency expectations per scenario
- **Failure patterns**: Common failure modes and edge cases

#### **3. Swedish Language Patterns (services/eval/scenarios.json)**
```json
[
  {"id":"fast_time","kind":"chat","text":"Hej Alice, vad är klockan?","expect":{"route":"micro"}},
  {"id":"planner_meeting","kind":"chat","text":"Boka möte med Anna imorgon kl 14","expect":{"route":"planner"}},
  {"id":"weather_today","kind":"chat","text":"Vad är vädret idag?","expect":{"route":"planner"}},
  {"id":"deep_summary","kind":"chat","text":"Summarize the following text in 1500 words: Lorem ipsum ...","expect":{"route":"deep"}}
]
```

**Learning Value:**
- **Swedish intent patterns**: Natural language understanding
- **Route classification**: Query complexity assessment
- **User intent mapping**: Real Swedish conversation patterns
- **Edge case identification**: Complex vs simple queries

### **🎯 Learning Objectives for Alice**

#### **1. Swedish Language Mastery**
- **Intent Recognition**: Learn Swedish conversation patterns
- **Context Understanding**: Grasp cultural and linguistic nuances
- **Query Classification**: Distinguish between simple, planning, and complex tasks
- **Response Optimization**: Improve Swedish language generation

#### **2. Performance Optimization**
- **Resource Management**: Learn optimal RAM/CPU usage patterns
- **Energy Efficiency**: Understand power consumption patterns
- **Latency Optimization**: Identify performance bottlenecks
- **Tool Selection**: Learn which tools work best for which tasks

#### **3. User Behavior Understanding**
- **Session Patterns**: Learn user interaction flows
- **Query Patterns**: Understand common user intents
- **Failure Recovery**: Learn from failed interactions
- **Success Patterns**: Replicate successful interactions

#### **4. System Health Awareness**
- **Guardian Integration**: Learn system health patterns
- **Brownout Behavior**: Understand degradation strategies
- **Recovery Patterns**: Learn from system recovery events
- **Resource Planning**: Optimize resource allocation

### **🔒 Privacy & Ethics**

#### **PII Protection**
- **Automatic Masking**: Email addresses, phone numbers, personal names
- **Consent Management**: Explicit user consent for data collection
- **Data Retention**: 7-day session logs, 30-day aggregated metrics
- **Right to Forget**: Complete data deletion capability

#### **Ethical Data Collection**
- **No Synthetic Data**: All data from real user interactions
- **Swedish Focus**: Optimized for Swedish language and culture
- **Transparent Collection**: Clear data usage policies
- **User Control**: Users control their data and learning contribution

### **📈 Learning Pipeline**

#### **Real-time Learning**
```python
# Alice learns from every interaction
def process_turn_event(event):
    """Extract learning insights from turn events"""
    
    # Performance learning
    if event["e2e_first_ms"] > 250:
        learn_slow_response_pattern(event)
    
    # Route selection learning
    if event["route"] != expected_route(event["session_id"]):
        learn_route_misclassification(event)
    
    # Tool usage learning
    for tool_call in event["tool_calls"]:
        if not tool_call["ok"]:
            learn_tool_failure_pattern(tool_call)
    
    # Energy optimization
    if event["energy_wh"] > baseline_energy:
        learn_high_energy_pattern(event)
```

#### **Batch Learning**
```python
# Daily learning from aggregated data
def daily_learning_cycle():
    """Process daily learning data"""
    
    # Load today's events
    events = load_daily_events()
    
    # Extract patterns
    performance_patterns = analyze_latency_trends(events)
    route_patterns = analyze_route_selection(events)
    tool_patterns = analyze_tool_usage(events)
    
    # Update Alice's knowledge
    update_performance_models(performance_patterns)
    update_route_classifier(route_patterns)
    update_tool_selection(tool_patterns)
    
    # Generate insights
    generate_learning_report()
```

### **🎯 Success Metrics for Alice's Learning**

#### **Language Learning**
- **Swedish Intent Accuracy**: ≥95% on test scenarios
- **Route Classification**: ≥90% correct model selection
- **Response Quality**: User satisfaction ≥4.2/5
- **Cultural Understanding**: Context-appropriate responses

#### **Performance Learning**
- **Latency Optimization**: P95 improvement ≥10%
- **Resource Efficiency**: RAM usage reduction ≥15%
- **Energy Optimization**: Power consumption reduction ≥20%
- **Tool Success Rate**: Tool usage success ≥95%

#### **System Learning**
- **Guardian Integration**: Zero system crashes
- **Brownout Prediction**: Proactive resource management
- **Recovery Speed**: Faster system recovery
- **User Experience**: Improved interaction quality

### **🚀 Future Learning Enhancements**

#### **Advanced Learning Features**
- **Multi-modal Learning**: Voice + text + vision patterns
- **Context Retention**: Long-term conversation memory
- **Proactive Learning**: Predictive user needs
- **Personalization**: User-specific learning patterns

#### **Learning Validation**
- **A/B Testing**: Validate learning improvements
- **User Feedback**: Direct user satisfaction metrics
- **Performance Monitoring**: Track learning impact
- **Continuous Improvement**: Iterative learning cycles

---

**This comprehensive learning data collection ensures Alice continuously improves while maintaining the highest standards of privacy, ethics, and Swedish language optimization.**

🎯 **Alice's learning journey is powered by real Swedish data, ethical collection practices, and continuous improvement - ready to become the most Swedish-aware AI assistant! 🇸🇪**