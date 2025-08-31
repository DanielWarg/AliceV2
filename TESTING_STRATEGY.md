# Alice v2 Testing Strategy
*Autonomous RealOps Testing Architecture with Self-Healing Capabilities*

## 🎯 Overview

Alice v2 implements a **RealOps testing approach** - no mocks, only real data flows through actual services. The testing system runs continuously, validates SLOs, detects regressions, applies safe remediation, and generates actionable reports.

**Philosophy**: Test with real Swedish voice data, actual SMTP/CalDAV integration, live RTSP streams, and production-equivalent LLM workloads. When issues arise, automatically fix them or create detailed issue reports.

## 🏗️ Testing Architecture

### Core Components
```
services/tester/
├── main.py                 # Test orchestrator & self-healing loop
├── scenarios.yaml          # Real E2E test scenarios
├── config.py              # Endpoints, accounts, SLO thresholds
├── runners/               # Component-specific test execution
│   ├── voice_ws.py        # Stream WAV files to /ws/asr (20ms chunks)
│   ├── nlu_eval.py        # Swedish intent classification accuracy
│   ├── planner_tools.py   # Real email/calendar/HA integration
│   ├── deep_eval.py       # Heavy reasoning workloads
│   └── vision_rtsp.py     # Live RTSP stream testing
├── chaos/                 # Resilience testing
│   ├── network_glitch.py  # DNS blackhole, timeouts
│   ├── rtsp_drop.py       # Camera disconnection simulation
│   └── tool_down.py       # MCP tool failure simulation
├── remedies/              # Self-healing actions
│   ├── guardian_actions.py # Lower RAG-K, disable Deep, prewarm Vision
│   └── service_restart.py # Graceful service restarts via API
├── metrics/               # SLO monitoring & reporting
│   ├── writer.py          # CSV/JSONL/Markdown output
│   └── analyzer.py        # Performance analysis & root cause detection
└── datasources/           # Real test data
    ├── common_voice/      # Swedish voice clips with transcripts
    ├── noise/             # Café, traffic, rain noise profiles
    └── prompts/           # Swedish text tasks for LLM evaluation
```

## 📊 SLO Targets & Validation

### Performance SLOs (P95 measurements)
- **Voice Pipeline**: End-to-end <2000ms
- **ASR Partial**: <300ms after speech detected
- **ASR Final**: <800ms after silence
- **Guardian Response**: <150ms state transitions
- **Micro LLM**: <250ms first token
- **Planner LLM**: <900ms first token, <1500ms complete
- **Deep LLM**: <1800ms first token, <3000ms complete
- **TTS Cached**: <120ms audio generation
- **TTS Uncached**: <800ms (≤40 characters)

### Quality SLOs
- **Swedish WER**: ≤7% clean audio, ≤11% with background noise
- **Intent Classification**: ≥92% accuracy on test suite
- **Tool Success Rate**: ≥95% for email/calendar/HA operations
- **Vision First Detection**: <350ms for still images
- **RTSP Reconnection**: <2s after connection drop

### Resource SLOs
- **Memory Usage**: <15GB total system RAM
- **Guardian Protection**: 0 system crashes from overload
- **Concurrent Deep Jobs**: Maximum 1 at any time
- **Energy Efficiency**: Smart scheduling during low battery

## 🧪 Test Scenarios

### Real Data Sources
**No synthetic data - everything uses production-equivalent inputs:**

1. **Swedish Voice Data**: Common Voice dataset with native speakers
2. **Background Noise**: Real café, street, office environments
3. **Email/Calendar**: Sandbox SMTP/IMAP and CalDAV accounts
4. **Home Assistant**: Development instance with simulated devices
5. **RTSP Streams**: Live camera feeds or public test streams
6. **LLM Prompts**: Actual Swedish conversation patterns and tasks

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
- Complex Reasoning: Document summarization, analysis → Deep LLM
- Tool Integration: Real email sending, calendar creation
- Guardian Integration: Brownout behavior during resource pressure
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
```

## 🚀 Implementation & Deployment

### Docker Integration
```yaml
# Add to docker-compose.yml
services:
  tester:
    build: ./services/tester
    container_name: alice-tester
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
      - ./services/tester/datasources:/data
      - ./services/tester/runs:/runs
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
docker compose up -d tester

# 4. Monitor test results
tail -f services/tester/runs/latest/log.jsonl
open services/tester/runs/latest/summary.md
```

## 🔒 Security & Privacy

### Test Data Protection
- **Sandbox Accounts**: Never use production email/calendar credentials
- **PII Masking**: Automatic detection and redaction in all logs
- **Audio Retention**: Generated TTS samples deleted after manual review
- **Consent Enforcement**: Block operations without proper scope permissions
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