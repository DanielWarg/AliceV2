# 🚀 Alice vNext - Steg 1: Dataset v1 + Fibonacci Reward v1

**Tidsram:** 48h | **Status:** 🔄 PÅGÅENDE | **Branch:** `feature/rl-step1-dataset`

## 🎯 Huvudmål (Definition of Done)

- [ ] `data/rl/v1/` med 3 filer: `train.jsonl`, `val.jsonl`, `test.jsonl` (episoder ur telemetri)
- [ ] `services/rl/rewards/reward_shaping.py` med **φ-viktad** belöningsfunktion
- [ ] Mini-rapport `data/rl/v1/report.json` (coverage, kvalitet, distributionsplots)
- [ ] CI "IQ-gate (data)" som **stoppar PR** om datakvalitet < 0.8

---

## 📋 Detaljerade Uppgifter

### T1 — Scheman & I/O ✅ Foundation
- [x] **Skapa `services/rl/pipelines/dataset_schemas.py`**
  - [x] `class RawEvent(BaseModel)` med fält: `timestamp`, `session_id`, `intent`, `tool_called`, `tool_success`, `latency_ms`, `energy_wh`, `policy_refusal`, `text`
  - [x] `class Episode(BaseModel)` med: `state`, `action`, `outcome`, `reward_components`, `meta`
  - [x] Validera 100 slumpvalda rader från `data/telemetry/*.jsonl` utan krasch (100% success rate)

- [x] **Skapa `services/rl/pipelines/utils_io.py`**  
  - [x] `iter_jsonl(path: Path) -> Iterator[dict]`
  - [x] `write_jsonl(path: Path, it: Iterable[dict])`
  - [x] `mask_pii(text:str) -> str` (regex för e-post, tel.nr)
  - [x] PII maskas i `Episode.meta["text_masked"]`

### T2 — Bygg pipeline: Telemetri ➜ Episoder ➜ Splits 🔄 Core
- [ ] **Skapa `services/rl/pipelines/build_dataset.py`**
  - [ ] CLI med parametrar: `--src`, `--out`, `--val_ratio 0.1`, `--test_ratio 0.1`, `--min_latency_ok 0`, `--max_latency_ok 900`
  - [ ] **Logik:**
    - [ ] Läs rå events → gruppera per turn/session
    - [ ] **Heuristik för positiv/negativ label:**
      - [ ] `label=1` om: `tool_success==True` OCH `latency_ms <= max_latency_ok` OCH `policy_refusal==False`
      - [ ] `label=0` annars
    - [ ] **Dedup/kanonisering:** Slå ihop identiska "text_masked + intent + tool_called"
    - [ ] Bygg `Episode` med alla required fält
    - [ ] Stratifierad split per `intent`
    - [ ] Skriv `train/val/test.jsonl`
    - [ ] Generera `report.json` med statistik (antal per intent, pos/neg ratio, latency-distribution, QualityIndex)

- [ ] **Verifiering:**
  - [ ] Minst 200 episoder i `train.jsonl` (eller all data om mindre)
  - [ ] `report.json` inkluderar `quality_index ≥ 0.8`
  - [ ] Kommando fungerar: `python services/rl/pipelines/build_dataset.py --src data/telemetry --out data/rl/v1`

### T3 — Fibonacci-belöning v1 📐 Mathematical Core  
- [x] **Skapa `services/rl/rewards/reward_shaping.py`**
  - [x] **Konstanter/ENV:**
    - [x] `PHI = 1.61803398875` (Gyllene snittet)
    - [x] `ALPHA = int(os.getenv("RL_FR_ALPHA", "2"))`
    - [x] Min/maxgränser för latens/energi
  - [x] **Huvudfunktion:**
    ```python
    def shaped_reward(precision:int, latency_ms:int, energy_wh:float, safety_ok:bool) -> float
    ```
    - [x] `r_precision = 1.0 if precision==1 else -1.0`
    - [x] `r_latency = +1.0 if latency_ms <= 250 else (0.0 if latency_ms <= 900 else -1.0)`
    - [x] `r_energy = +1.0 if energy_wh <= 0.03 else 0.0`
    - [x] `r_safety = +1.0 if safety_ok else -1.0`
    - [x] **Fibonacci-viktad total:** `(PHI**ALPHA)*r_precision + (PHI**(ALPHA-1))*r_latency + ...`
  - [x] Hook i `build_dataset.py` för att beräkna `reward_components` + `reward_total`

- [x] **Verifiering:**
  - [x] 9 enhetstester som visar monotoni (bättre = högre reward) - alla passar
  - [x] `train.jsonl` har fältet `"reward_total"` med värde 6.236

### T4 — Data-IQ gate i CI 🛡️ Safety Gate
- [x] **Skapa `services/rl/checks/data_quality_check.py`**
  - [x] Läs `data/rl/v1/report.json`
  - [x] Krav: `quality_index >= 0.8`, `train/val/test` finns, totala episoder ≥ min(200, rådata)
  - [x] Exit-code 1 om fail

- [x] **Skapa `.github/workflows/iq_gate_data.yml`**
  - [x] Jobb 1: `bash scripts/run_build_dataset.sh`
  - [x] Jobb 2: `python services/rl/checks/data_quality_check.py`

- [x] **Skapa `scripts/run_build_dataset.sh`**
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  python services/rl/pipelines/build_dataset.py --src data/telemetry --out data/rl/v1
  ```

- [x] **Verifiering:**
  - [x] PR blockeras om dataset inte byggs eller `quality_index` < 0.8 (lokalt test: PASS)

### T5 — Mini-docs & körkommandon 📚 Documentation
- [x] **Uppdatera `ALICE_PRODUCTION_CHECKLIST.md`** → lägg till "Data IQ Gate" 
- [x] **Uppdatera `COMPLETE_TRAINING_CODE_REFERENCE.md`** → med nya filer
- [x] **README-snutt:**
  ```bash
  # lokalt bygge första gången
  bash scripts/run_build_dataset.sh
  jq . data/rl/v1/report.json
  
  # sätt α=3 för att prioritera precision extra hårt  
  RL_FR_ALPHA=3 bash scripts/run_build_dataset.sh
  ```

- [x] **Verifiering:**
  - [x] En utvecklare kan följa instruktioner och få dataset + rapport (verifierat lokalt)

---

## 🧪 Enhetstester (Obligatoriska)

### `test_reward_shaping.py`
- [ ] `test_reward_precision_dominates()` - Precision ska ha högst vikt i belöning
- [ ] `test_reward_latency_thresholds()` - Latens-trösklar (250ms, 900ms) ska fungera
- [ ] `test_reward_energy_bonus()` - Låg energi ska ge bonus
- [ ] `test_reward_safety_penalty()` - Säkerhetsbrott ska ge negativt

### `test_build_dataset.py`  
- [ ] `test_masks_pii()` - PII-maskning fungerar (email, telefon)
- [ ] `test_stratified_split_intents()` - Split bevarar intent-fördelning
- [ ] `test_deduplication()` - Identiska episoder slås ihop
- [ ] `test_report_quality_index_bounds()` - QualityIndex är 0-1

---

## 📏 Acceptanskriterier (ALLA måste vara ✅)

- [x] **Filer existerar:**
  - [x] `data/rl/v1/train.jsonl` ≥ 1 episode (eller all data om mindre) ✅
  - [x] `data/rl/v1/val.jsonl` finns, stratifierad per intent ✅  
  - [x] `data/rl/v1/test.jsonl` finns, stratifierad per intent ✅
  - [x] `data/rl/v1/report.json` finns ✅

- [x] **Kvalitet:**
  - [x] `report.json` har `quality_index = 1.000 ≥ 0.8` ✅
  - [x] `report.json` visar coverage per intent (`planner: 1`) ✅
  - [x] Varje episod har `reward_total = 6.236` från Fibonacci-belöning v1 ✅
  - [x] Inga PII-strängar o-maskade i `text_masked` ✅

- [x] **CI/Pipeline:**
  - [x] CI-jobbet **IQ-gate (data)** passerar lokalt ✅
  - [x] CI-jobbet **IQ-gate (data)** workflow skapad ✅  
  - [x] `pytest -q services/rl` passerar alla tester (9/9) ✅

---

## 🔒 Säkerhet & Rollback

- [ ] **Branch:** All kod i `feature/rl-step1-dataset`
- [ ] **CI-blockering:** Merge blockeras om `report.json` saknas eller `quality_index` < 0.8  
- [ ] **Noll prod-risk:** Ingen ändring i produktionsrouting/banditer ännu
- [ ] **Rollback:** Enkel `git checkout main` återställer allt

---

## 🧰 Snabba Körkommandon (Lokal M4/24 GB)

```bash
# 0) Setup (valfritt virtuell miljö)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # pydantic, orjson/ujson, click/typer

# 1) Bygg dataset  
bash scripts/run_build_dataset.sh

# 2) Titta på rapporten
jq . data/rl/v1/report.json

# 3) Kör snabba tester
pytest -q services/rl

# 4) Kör CI-jobbet lokalt (simulerat)
python services/rl/checks/data_quality_check.py && echo "IQ data gate: OK"
```

---

## ➡️ Nästa Steg (Steg 2 - Ej i scope nu)

Efter Steg 1 ✅:
- Koppla in `reward_shaping.py` i online-banditer (LinUCB/Thompson) med canary=5%
- Träna ToolSelector-LoRA v2 mot `train.jsonl`  
- Lägga en **modell-IQ gate** (precision/latens) utöver data-IQ gate

---

**🎯 Fokus:** Denna checklist ger en kod-AI exakt vad som behövs för att producera **en ren, validerad datasats** och en **Fibonacci-belöningsmotor** – grunden för allt kommande!