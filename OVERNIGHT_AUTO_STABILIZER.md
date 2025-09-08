# Overnight Auto-Stabilizer Guide

## 🌙 Overview
**8-hour autonomous optimization** that "tickar" while you sleep and delivers concrete improvement suggestions by morning.

## 🎯 What It Does

### Every 10 minutes (48 cycles total):
- Ingests fresh prod telemetry 
- Captures drift snapshot (PSI/KS/verifier_fail)
- Appends to history for trending

### Every hour (8 times total):
- Runs RCA failure sampling (PII-masked)
- Analyzes top failure patterns
- Builds failure pattern histogram

### After 8 hours:
- **Off-policy experiments:** Tests FormatGuard max_chars (±10%) against collected failures
- **Intent analysis:** Extracts Swedish keywords from "unknown" intents → suggests regex buckets
- **Generates morning report:** Concrete suggestions in `ops/suggestions/`

## 🚀 How to Run

### Start 8-hour run:
```bash
# Foreground (blocks terminal)
make overnight-8h

# Background with tmux  
bash ops/scripts/run_overnight_tmux.sh
# Later attach: tmux attach -t alice_overnight
```

### Check results (next morning):
```bash
make morning-report
```

## 📊 Expected Output

### Files generated in `ops/suggestions/`:
- `morning_report.md` - Human-readable summary with actionable checklist
- `morning_report.json` - Structured data for automation
- `formatguard_suggestion.json` - Optimized max_chars proposal
- `intent_regex_suggestions.yaml` - New intent bucket patterns

### Morning report contains:
- **Drift trends:** 8-hour PSI/KS/verifier_fail progression
- **Top-3 RCA patterns:** Most common failure causes
- **FormatGuard optimization:** Proposed max_chars that would prevent most failures
- **Intent regex suggestions:** Swedish keywords → finance/code/travel buckets
- **Actionable checklist:** Ready-to-apply staging tests

## ✅ Safety & Compliance

- **Off-policy only:** Never modifies prod configuration
- **PII-safe:** Uses existing masking (emails→EMAIL_hash, phones→PHONE_hash)
- **Non-invasive:** Only reads telemetry and logs, never writes to prod systems
- **Graceful:** Continues if individual cycles fail

## 📋 Next Steps After Running

1. **Apply FormatGuard proposal:**
   ```bash
   # Use suggested max_chars in staging
   export FORMATGUARD_MAX_CHARS=<proposal_max_chars>
   make smoke-test
   ```

2. **Test intent regex suggestions:**
   - Add proposed finance/code/travel patterns to intent classification
   - Measure PSI reduction

3. **Address top RCA patterns:**
   - Fix top-3 failure causes identified in report
   - Re-run `halfday-loop` to validate improvements

4. **Continue structured testing:**
   ```bash
   make halfday-loop  # Until verifier_fail ≤ 1.0%
   make soak-check    # 72h validation  
   make go-check      # GO/NO-GO decision
   ```

## 🔧 Technical Details

### Data Sources:
- `data/logs/prod_requests.jsonl` - Production request logs
- `data/ops/telemetry_window.json` - Aggregated metrics window
- `data/ops/drift_history.jsonl` - Historical drift measurements

### Analysis Methods:
- **Stratified sampling:** Ensures representative failure coverage across routes/intents  
- **Swedish NLP:** Regex extraction with stopword filtering for intent suggestions
- **Off-policy simulation:** Tests parameter changes against historical failures
- **Rolling metrics:** 8-hour trends for stable measurement

This system delivers **konkreta, säkra förbättringsförslag** without touching production, ready for staging validation and GO decision.