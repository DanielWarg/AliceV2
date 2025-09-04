# Alice v2 - Daily Status & Next Steps

_Uppdaterad: 2025-09-01 - Eftermiddagsrapport_

## 🎯 **DAGENS SLUTSTATUS**

### ✅ **VAD VI HAR GJORT IDAG**

Kort: Docker-only dev-proxy, Observability+HUD klart, `/metrics` exponerad, NLU-service scaffoldad, curator/scheduler pipeline på plats (scheduler optional), Orchestrator↔Guardian URL fix, NLU-proxy routing, auto_verify uppdaterad.

1. **🤖 LLM Drivers Implementerade:**
   - `services/orchestrator/src/llm/ollama_client.py` - Ollama client med timeouts
   - `services/orchestrator/src/llm/micro_phi.py` - Phi-mini driver för snabba svar
   - `services/orchestrator/src/llm/planner_qwen.py` - Qwen-MoE driver med JSON output
   - `services/orchestrator/src/llm/deep_llama.py` - Llama-3.1 driver med Guardian integration

2. **🧠 Intelligent Routing:**
   - `services/orchestrator/src/router/policy.py` - Pattern matching för micro/planner/deep
   - Testat och fungerar: "Hej Alice" → micro, "Boka möte" → planner, "Analysera" → deep

3. **📋 Planner Execution:**
   - `services/orchestrator/src/planner/schema.py` - JSON schema för tool execution
   - `services/orchestrator/src/planner/execute.py` - Plan execution med fallback matrix

4. **🛡️ Guardian Integration:**
   - Deep model blocked under brownout
   - Planner degraded under resurstryck
   - Micro always available

5. **🐳 Docker-only + Dev-proxy (18000):**
   - `ops/Caddyfile` - Proxy till orchestrator/guardian/HUD/NLU
   - `scripts/dev_up.sh`/`dev_down.sh` - Deterministisk start/stop
   - Compose: inga host-portar utom proxy; healthchecks på alla services

6. **📈 Observability & Metrics:**
   - `/metrics` endpoint i Orchestrator (Prometheus-format)
   - P50/P95 per route via middleware; `/api/chat` sätter `X-Route` tidigt
   - Turn events (JSONL) med RAM-peak, energy Wh, input/output/lang under `data/telemetry/YYYY-MM-DD/`

7. **🧠 NLU-service (svenska) – v1 scaffold:**
   - `services/nlu/` (FastAPI) med `/api/nlu/parse`
   - Baseline intents/slots (regex + dateparser), proxy routing via `/api/nlu/*`
   - Orchestrator anropar NLU och sätter `X-Intent`/`X-Route-Hint`

8. **🪄 Dataloop (curator):**
   - `services/curator/` + `ops/schedule.cron` (indexer commented)
   - `scripts/auto_verify.sh` kör curator och sparar summary

9. **🧠 NLU v1 (svenska):**
   - `/api/nlu/parse` aktiv; e5-embeddings + heuristik
   - Orchestrator `/api/chat` sätter `X-Intent`/`X-Route-Hint` och `X-Route`
   - Eval-svit utökad till 20 scenarier (micro/planner) – 100% pass
   - Cron installerad: auto_verify kl 14:00 → `logs/auto_verify.log`

## 🚨 **AKTUELLT PROBLEM**

Alla tidigare portkrockar eliminerade med Docker-only + dev-proxy. Scheduler-bild är optional (kan lämnas av tillsvidare). Ollama tillagd i compose; modell-pull och val av mikro-modell sker i nästa steg.

### **Kvarstående småsaker:**

1. NLU ONNX (multilingual-e5-small) + XNLI (int8) och threshold-tuning
2. Micro-LLM (Phi-mini) via Ollama (modell-pull och sanity)
3. Scheduler-image (cron) kan bytas till publik om nattkörningar önskas i dev

## 🚀 **NÄSTA STEG (IMORGON)**

### **Steg 1: Start & Sanity**

```bash
scripts/dev_up.sh
curl -s http://localhost:18000/health | jq .
curl -s http://localhost:18000/api/status/routes | jq .
```

### **Steg 2: NLU + Mikro-LLM**

```bash
# NLU sanity
curl -s -X POST http://localhost:18000/api/nlu/parse -H 'Content-Type: application/json' \
  -d '{"v":"1","lang":"sv","text":"Boka möte med Anna imorgon kl 14","session_id":"nlu-sanity"}' | jq .

# (Efter modell-pull) mikro-LLM sanity
curl -s -X POST http://localhost:18000/api/orchestrator/chat -H 'Content-Type: application/json' \
  -d '{"v":"1","session_id":"dev","lang":"sv","message":"Hej Alice, vad är klockan?"}' | jq .
```

### **Steg 3: Validera System**

```bash
./scripts/auto_verify.sh
cat data/tests/summary.json | jq .
open http://localhost:18000/hud
```

### **Steg 4: Nästa Prioritet**

Om LLM integration fungerar → **Voice Pipeline Implementation**

- ASR→NLU→TTS pipeline med WebSocket connections
- Svenska språkmodeller (Whisper ASR)
- Utöka `services/eval/scenarios.json` med voice scenarios

## 📋 **ACCEPTANSKRITERIER**

### **LLM Integration v1 är klar när:**

- [ ] **Routing fungerar**: micro/planner/deep routes väljs korrekt
- [ ] **LLM drivers fungerar**: Ollama integration med proper timeouts
- [ ] **Planner execution**: JSON schema validation + tool execution
- [ ] **Guardian integration**: Deep blocked i brownout, planner degraded
- [ ] **Fallback matrix**: LLM + tool fallback med max 1 kedja per turn
- [ ] **SLO compliance**: Fast ≤250ms, planner ≤1500ms, deep ≤3000ms
- [ ] **Eval harness**: 20 scenarier passerar med ≥80% success rate

## 🔧 **TEKNISKA DETALJER**

### **Branch:**

- `feat/llm-integration-v1` - Alla ändringar committade

### **Nyckelfiler:**

- `services/orchestrator/src/llm/` - LLM drivers
- `services/orchestrator/src/router/` - Intelligent routing
- `services/orchestrator/src/planner/` - Planner execution
- `scripts/ports-kill.sh` - Port cleanup
- `scripts/start-llm-test.sh` - LLM test script

### **Miljövariabler:**

```bash
OLLAMA_HOST=http://ollama:11434
LLM_MICRO=phi3.5:mini
LLM_PLANNER=qwen2.5:7b-moe
LLM_DEEP=llama3.1:8b
LLM_TIMEOUT_MS=1800
```

## 🎯 **SUCCESS METRICS**

### **Tekniska:**

- Routing accuracy: ≥90% korrekt route selection
- LLM response time: Inom SLO (≤250ms, ≤1500ms, ≤3000ms)
- Guardian integration: Deep blocked under brownout
- Fallback success: ≥80% fallback success rate

### **Business:**

- E2E test success: ≥80% pass rate
- System stability: Inga crashes under normal load
- Observability: Alla metrics loggade korrekt

---

**NÄSTA AI AGENT**: Du har allt du behöver! Starta med `./scripts/ports-kill.sh` och `./scripts/start-llm-test.sh`, testa LLM integrationen, och validera att allt fungerar enligt acceptanskriterierna ovan.
