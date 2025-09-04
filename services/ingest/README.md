# Test → Alice Smart Ingestion Module (v1)

Gör att all **riktig testtrafik** (eval-harness + e2e) sparas som **lärbar, kuraterad träningssignal** för Alice – utan mocks. Modulen matar observability, förbättrar NLU/planerare, och producerar säkra, versionerade datapack.

## 🎯 Mål

- Samla **riktiga** turn-events/tests → normalisera → kvalitetssäkra → lagra → exportera.
- Driva **kontinuerligt lärande** (NLU thresholds, planner-policies, RAG K, cache/prewarm).
- Hålla **compliance & säkerhet**: PII-maskning, consent, "right-to-forget".

## ✨ Vad ingår (v1)

1. **Ingestion**: läser `data/telemetry/**/events.jsonl` + `data/tests/results.jsonl` (eval-harness).
2. **Normalizer**: mappar fält till ett stabilt schema v1 (se JSON nedan).
3. **Governance**: PII-mask, consent-scopes, anomali-flaggor; red-team-taggar.
4. **Signals**: beräknar features (latens, RAG-hit, tool-errorklass, energikostnad, NLU-marginal, injection score).
5. **Exporters**:
   - `parquet/` för analys/ML.
   - `snapshots/` för versionerade datapack.
   - `prom` counters för "learning rate" (hur mycket nytt lärbart per dag).

6. **Dash-hooks**: visar daglig learning-rate, data-kvalitet, drift.
7. **APIs**: `/api/learn/ingest` (ad-hoc), `/api/learn/snapshot` (stänger dag), `/api/learn/stats`.

---

## 🗂️ Filstruktur

```
/data
  /telemetry/YYYY-MM-DD/events.jsonl          # turn-events (prod/dev)
  /tests/results.jsonl                         # eval-harness utfall
  /learn/
    /parquet/YYYY-MM-DD/*.parquet             # normaliserad data
    /snapshots/YYYY-MM-DD/dataset.jsonl.gz    # dagliga datapack
    /logs/learn.jsonl                         # ingest-logg
```

---

## ⚙️ Env & konfig

```env
LEARN_ENABLED=true
LEARN_INPUT_DIR=data/telemetry
LEARN_TESTS_FILE=data/tests/results.jsonl
LEARN_OUT_PARQUET=data/learn/parquet
LEARN_OUT_SNAPSHOT=data/learn/snapshots
LEARN_LOG=data/learn/logs/learn.jsonl
LEARN_PII_POLICY=bronze          # bronze|silver|gold
LEARN_MASK_EMAIL=true
LEARN_MASK_PHONE=true
LEARN_MASK_SSN=true
LEARN_MIN_CONF=0.60              # min intent confidence för "learnable"
LEARN_MIN_MARGIN=0.05            # NLU margin för learnable
LEARN_DENY_STRICT=true           # exkludera STRICT/LOCKDOWN turns
```

---

## 📦 JSON-schema (v1) – normaliserad rad

```json
{
  "v": "1",
  "ts": "2025-09-01T14:00:22.123Z",
  "trace_id": "b2a3...",
  "session_id": "s-123",
  "route": "micro|planner|deep",
  "lang": "sv",
  "user_text": "hej alice ...",
  "response_text": "hej! ...",
  "nlu": {
    "intent": "calendar.create",
    "conf": 0.86,
    "margin": 0.21,
    "slots": { "time": "2025-09-02T14:00:00+02:00" }
  },
  "timings": {
    "ttft_ms": 120,
    "full_ms": 480,
    "p50_route_ms": 8.6,
    "p95_route_ms": 24.7
  },
  "rag": { "top_k": 3, "hits": 2 },
  "tools": [{ "name": "calendar.read", "ok": true, "klass": null, "lat_ms": 85 }],
  "security": {
    "mode": "NORMAL",
    "inj_score": 0.13,
    "sanitised": false,
    "system_prompt_sha256": "a1b2..."
  },
  "resources": {
    "ram_peak_mb": { "proc": 410.2, "sys": 7341.5 },
    "energy_wh": 0.0031
  },
  "outcome": {
    "ok": true,
    "error": null,
    "labels": ["eval", "prod"],
    "redteam": false
  },
  "consent": {
    "scopes": ["mail:metadata"],
    "pii_masked": true
  }
}
```

> Obs: i ingest maskas `user_text`/`slots` enligt PII-policy; råtext sparas aldrig i "silver/bronze".

---

## 🧪 Lärbarhets-regler (v1)

- **Ta med** rader där:
  - `outcome.ok == true`
  - `nlu.conf >= LEARN_MIN_CONF` **och** `nlu.margin >= LEARN_MIN_MARGIN`
  - `security.mode == "NORMAL"` (om `LEARN_DENY_STRICT=true`)
  - **ej** `redteam`

- **Tagga** svåra case:
  - Låg marginal (`nlu.margin < 0.08`) → `labels += ["hard_intent"]`
  - Tool-fel (`tools[].ok==false`) → `labels += ["tool_fail"]`
  - RAG=0 → `labels += ["rag_miss"]`

---

## 🛠️ API (FastAPI – orkestratorn)

- `POST /api/learn/ingest` → kör en runda (returnerar antal rader in/ut + orsak till drop)
- `POST /api/learn/snapshot` → skriver dags-snapshot (`dataset.jsonl.gz`) + checksum
- `GET  /api/learn/stats` → sammanfattning (dag/vecka), learning-rate, kvalitetsindikatorer

**Exempelrespons /api/learn/stats**

```json
{
  "v": "1",
  "day": "2025-09-01",
  "rows_raw": 1240,
  "rows_learnable": 812,
  "hard_intent": 73,
  "tool_fail": 19,
  "rag_miss": 41,
  "learning_rate": 0.65,
  "snapshot": "data/learn/snapshots/2025-09-01/dataset.jsonl.gz"
}
```

---

## 🧵 Pipelines (CLI/Make)

```bash
# engång
make venv && source .venv/bin/activate
bash scripts/fetch_models.sh

# kör ingest + snapshot manuellt
python services/ingest/run_ingest.py \
  --input data/telemetry \
  --tests data/tests/results.jsonl \
  --parquet_out data/learn/parquet \
  --snapshot_out data/learn/snapshots \
  --log_out data/learn/logs/learn.jsonl

# make targets (lägg i Makefile)
learn:
	python services/ingest/run_ingest.py --input $(LEARN_INPUT_DIR) --tests $(LEARN_TESTS_FILE) --parquet_out $(LEARN_OUT_PARQUET) --snapshot_out $(LEARN_OUT_SNAPSHOT) --log_out $(LEARN_LOG)

learn-daily:
	curl -s -X POST http://localhost:8000/api/learn/snapshot | jq .
```

**Cron (dagligen 14:00, host):**

```
0 14 * * * cd /path/to/repo && make learn >> logs/learn.log 2>&1
```

---

## 📈 Dashboard (HUD) – nya paneler

- **Learning rate** (daglig andel learnable av rådata)
- **Hard intents** (antal/mix)
- **Tool-fail per klass** (stack) – hjälper planner/tool-stabilisering
- **RAG miss rate** (andel turns utan träff)
- **Energy/turn & RAM-peak distribution** (sanity + eco)

Källa: läs `data/learn/parquet/` + `learn.jsonl` eller Prom counters.

---

## 🔒 Governance & säkerhet

- **PII-mask** alltid i normaliserad data (e-post/telefon/PNR).
- **Consent scopes** sparas; **user memory** kräver explicit consent och skrivs separat (ej i denna modul).
- **Right-to-forget**: API ska radera matchande `session_id`/`trace_id` från `parquet/` och `snapshots/` + logga ett `forget_event` (mål < 1s).

---

## ✅ Definition of Done (v1)

- [ ] `learn` körs automatiskt 14:00 (cron/CI).
- [ ] **Parquet** + **snapshot (.jsonl.gz + sha256)** produceras dagligen.
- [ ] **Pass-regler** appliceras (confidence/margin/security/redteam).
- [ ] **PII-mask** och **consent** följer policy (bronze/silver/gold).
- [ ] **HUD** visar learning-rate, hard_intent, tool_fail, rag_miss.
- [ ] **Right-to-forget** testad e2e (<1s).
- [ ] **/api/learn/stats** rapporterar dagliga siffror.

---

## 🧩 Snabb Pydantic-modell (om ni vill validera in-schema)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class LearnRow(BaseModel):
    v: str = "1"
    ts: str
    trace_id: str
    session_id: str
    route: str
    lang: str
    user_text: Optional[str]
    response_text: Optional[str]
    nlu: Dict[str, Any]
    timings: Dict[str, Any]
    rag: Dict[str, Any]
    tools: List[Dict[str, Any]]
    security: Dict[str, Any]
    resources: Dict[str, Any]
    outcome: Dict[str, Any]
    consent: Dict[str, Any]
```

---

## 🔍 Mini-checklista att bocka av i PR

- [ ] `services/ingest/run_ingest.py` finns (ingest + normalize + export).
- [ ] Env-variabler enligt ovan; defaultar till `/data/...`.
- [ ] `/api/learn/*` endpoints inkopplade.
- [ ] `Makefile` targets `learn` och `learn-daily`.
- [ ] Cron/CI kör 14:00.
- [ ] HUD-sektion "Learning" aktiverad.
- [ ] DoD-punkter gröna.

---

## 🧠 Vad modulen lär Alice (konkret)

- **NLU**: thresholds/margins justeras med verkliga svåra intents ("hard_intent").
- **Planner/Tools**: vilka verktyg fallerar var – förbättra fallback och schema.
- **RAG**: tunar K/indextyper när `rag_miss` sticker.
- **Eco/SLO**: energi/turn och RAM-peak ger cache/prewarm-förslag.
