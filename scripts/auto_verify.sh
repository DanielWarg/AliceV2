#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:18000}"
GUARD_BASE="${GUARD_BASE:-http://localhost:18000}"
DASH_URL="${DASH_URL:-http://localhost:18000}"
ART_DIR="${ART_DIR:-data/tests}"
TEL_DIR="${TEL_DIR:-data/telemetry}"
SLO_FAST_P95=${SLO_FAST_P95:-250}
SLO_PLANNER_FULL_P95=${SLO_PLANNER_FULL_P95:-1500}
SLO_DEEP_FULL_P95=${SLO_DEEP_FULL_P95:-3000}
GUARD_TRIGGER_MS=${GUARD_TRIGGER_MS:-150}
GUARD_RECOVER_S=${GUARD_RECOVER_S:-60}

# Enhanced validation settings
MIN_SAMPLES_PER_ROUTE=${MIN_SAMPLES_PER_ROUTE:-500}
# Optional focus route (e.g., planner|micro|deep). If set, gating only checks that route
FOCUS_ROUTE="${FOCUS_ROUTE:-}"
MAX_TAIL_PERCENT=${MAX_TAIL_PERCENT:-1}  # Max 1% of requests > 1.5s
MIN_SCHEMA_OK_RATE=${MIN_SCHEMA_OK_RATE:-99}  # Min 99% schema success
MAX_FALLBACK_RATE=${MAX_FALLBACK_RATE:-1}  # Max 1% fallback usage

# Host safety limits (lightweight resource guard)
MAX_LOAD=${MAX_LOAD:-3.5}                 # Max 1-min load avg before throttling
MIN_BATT_PCT=${MIN_BATT_PCT:-30}         # Min battery percent if on battery
SAFETY_SLEEP=${SAFETY_SLEEP:-5}          # Seconds to pause when over limits
THROTTLE_SLEEP=${THROTTLE_SLEEP:-0.05}   # Per-iteration sleep when throttled
LOAD_CHECK_EVERY=${LOAD_CHECK_EVERY:-25} # Re-check cadence during loops
SAFETY_THROTTLED=0

# Traffic generation parameters (counts + customizable messages)
MICRO_LOOPS=${MICRO_LOOPS:-50}
PLANNER_LOOPS=${PLANNER_LOOPS:-1500}
# When focusing on a route, allow separate loop override
PLANNER_LOOPS_FOCUS=${PLANNER_LOOPS_FOCUS:-4000}
MICRO_MESSAGE=${AUTO_VERIFY_MICRO_MESSAGE:-"Hej Alice, vad är klockan?"}
# Use a phrase that maps to planner via NLU (calendar/email intents)
PLANNER_MESSAGE=${AUTO_VERIFY_PLANNER_MESSAGE:-"Boka möte med Anna imorgon kl 14:00"}

# SAFE_MODE: conservative defaults to protect host
SAFE_MODE=${SAFE_MODE:-false}
if [ "$SAFE_MODE" = "true" ]; then
  MAX_LOAD=${MAX_LOAD:-2.5}
  MIN_BATT_PCT=${MIN_BATT_PCT:-35}
  THROTTLE_SLEEP=${THROTTLE_SLEEP:-0.08}
  LOAD_CHECK_EVERY=${LOAD_CHECK_EVERY:-10}
  if [ -z "$FOCUS_ROUTE" ]; then FOCUS_ROUTE=planner; fi
  MICRO_LOOPS=0
  PLANNER_LOOPS=200
  PLANNER_LOOPS_FOCUS=200
  echo "🛡️  SAFE_MODE enabled: load<=${MAX_LOAD}, batt>=${MIN_BATT_PCT}%, loops(planner)=${PLANNER_LOOPS}, throttle=${THROTTLE_SLEEP}s"
fi

# --- Resource guard helpers (macOS-friendly, no sudo required) ---
os_name=$(uname -s 2>/dev/null || echo "")

get_load() {
  if command -v sysctl >/dev/null 2>&1; then
    # macOS: returns like "{ 1.23 1.45 1.60 }" → pick first value
    sysctl -n vm.loadavg 2>/dev/null | awk -F'[ {}]+' '{print $2}'
  else
    # Fallback: parse from uptime output
    uptime 2>/dev/null | awk -F'load averages?: ' '{print $2}' | awk -F', ' '{print $1}'
  fi
}

get_battery_pct() {
  if command -v pmset >/dev/null 2>&1; then
    pmset -g batt 2>/dev/null | grep -Eo '[0-9]+%' | tr -d '%'
  else
    echo "-1"
  fi
}

is_on_ac_power() {
  if command -v pmset >/dev/null 2>&1; then
    pmset -g batt 2>/dev/null | head -n1 | grep -qi 'AC Power' && return 0 || return 1
  fi
  return 0
}

resource_guard() {
  local load batt ac
  load=$(get_load || echo "0")
  batt=$(get_battery_pct || echo "-1")
  if is_on_ac_power; then ac=1; else ac=0; fi

  # Decide throttle/pausing
  local over_load=0 low_batt=0
  awk "BEGIN{exit !($load > $MAX_LOAD)}" && over_load=1 || over_load=0
  if [ "$ac" -eq 0 ] && [ "$batt" -ge 0 ] && [ "$batt" -lt "$MIN_BATT_PCT" ]; then
    low_batt=1
  fi

  if [ "$over_load" -eq 1 ] || [ "$low_batt" -eq 1 ]; then
    SAFETY_THROTTLED=1
    echo "⚠️  Resource guard active (load=${load}, batt=${batt}%, ac=${ac}). Throttling..."
    # Reduce loops to keep system cool
    if [ "${FOCUS_ROUTE:-}" = "planner" ]; then
      PLANNER_LOOPS_FOCUS=$(( PLANNER_LOOPS_FOCUS>200 ? 200 : PLANNER_LOOPS_FOCUS ))
      PLANNER_LOOPS=$(( PLANNER_LOOPS>200 ? 200 : PLANNER_LOOPS ))
    else
      PLANNER_LOOPS=$(( PLANNER_LOOPS>200 ? 200 : PLANNER_LOOPS ))
      MICRO_LOOPS=$(( MICRO_LOOPS>25 ? 25 : MICRO_LOOPS ))
    fi
    echo "   → Loops: planner=${PLANNER_LOOPS} (focus=${PLANNER_LOOPS_FOCUS:-n/a}), micro=${MICRO_LOOPS}"
    echo "   → Cooling pause ${SAFETY_SLEEP}s..."; sleep "$SAFETY_SLEEP" || true
  fi
}

mkdir -p "$ART_DIR"
> "$ART_DIR/results.jsonl"

# Progress log
PROG_LOG="$ART_DIR/progress.log"
> "$PROG_LOG"

# Watchdog & health guards
TIME_CAP_S=${TIME_CAP_S:-0}                 # 0 = disabled
REPORT_INTERVAL=${REPORT_INTERVAL:-15}      # seconds between progress reports
ABORT_ON_UNHEALTHY=${ABORT_ON_UNHEALTHY:-true}
ABORT_ON_P95_MS=${ABORT_ON_P95_MS:-0}       # 0 = disabled
ABORT_ON_SCHEMA_OK=${ABORT_ON_SCHEMA_OK:-0} # 0 = disabled (% threshold)

TODAY=$(date +%F)
TEL_FILE="$TEL_DIR/$TODAY/events_$TODAY.jsonl"

sec_now(){ date +%s; }

watchdog_check(){
  local now=$(sec_now)
  # Time cap
  if [ "${TIME_CAP_S:-0}" -gt 0 ] && [ $(( now - STAGE_T0 )) -gt "$TIME_CAP_S" ]; then
    echo "⏱️  TIME_CAP hit ($((now-STAGE_T0))s > ${TIME_CAP_S}s) – aborting step" | tee -a "$PROG_LOG"
    exit 1
  fi
  # Health checks
  if [ "${ABORT_ON_UNHEALTHY}" = "true" ]; then
    curl -fsS "$API_BASE/health" >/dev/null 2>&1 || { echo "❌ Orchestrator unhealthy – abort" | tee -a "$PROG_LOG"; exit 1; }
    curl -fsS "$API_BASE/ollama/api/tags" >/dev/null 2>&1 || { echo "❌ Ollama unhealthy – abort" | tee -a "$PROG_LOG"; exit 1; }
  fi
  # Quick P95 gate
  if [ "${ABORT_ON_P95_MS:-0}" -gt 0 ]; then
    local p95 raw
    raw=$(curl -fsS "$API_BASE/api/status/routes" 2>/dev/null | jq -r '.planner_p95_ms // 0' || echo 0)
    # Cast float/null safely to integer milliseconds
    if [ "$raw" = "null" ] || [ -z "$raw" ]; then p95=0; else p95=$(printf '%.0f' "$raw" 2>/dev/null || echo 0); fi
    if [ "$p95" -gt "$ABORT_ON_P95_MS" ]; then
      echo "❌ planner P95=${p95}ms > ${ABORT_ON_P95_MS}ms – abort" | tee -a "$PROG_LOG"
      exit 1
    fi
  fi
  # Quick schema_ok estimate from recent telemetry (last 200 lines)
  if [ "${ABORT_ON_SCHEMA_OK:-0}" -gt 0 ] && [ -f "$TEL_FILE" ]; then
    local last total ok pct
    last=$(tail -n 200 "$TEL_FILE" 2>/dev/null || true)
    total=$(echo "$last" | grep -c '"route": "planner"' || true)
    if [ "$total" -gt 0 ]; then
      ok=$(echo "$last" | grep -c '"planner_schema_ok": true' || true)
      pct=$(awk -v a=$ok -v b=$total 'BEGIN{printf("%d", (a>0&&b>0)?(a*100.0/b):0)}')
      if [ "$pct" -lt "$ABORT_ON_SCHEMA_OK" ]; then
        echo "❌ schema_ok ${pct}% < ${ABORT_ON_SCHEMA_OK}% – abort" | tee -a "$PROG_LOG"
        exit 1
      fi
    fi
  fi
}

progress_report(){
  local now=$(sec_now)
  if [ $(( now - LAST_REPORT )) -ge "$REPORT_INTERVAL" ]; then
    local p95 raw
    raw=$(curl -fsS "$API_BASE/api/status/routes" 2>/dev/null | jq -r '.planner_p95_ms // 0' || echo 0)
    if [ "$raw" = "null" ] || [ -z "$raw" ]; then p95=0; else p95=$(printf '%.0f' "$raw" 2>/dev/null || echo 0); fi
    echo "📊 progress t+$((now-STAGE_T0))s p95=${p95}ms" | tee -a "$PROG_LOG"
    LAST_REPORT=$now
  fi
}

echo "▶️  Startar tjänster via docker compose (docker-only)…"
docker compose up -d guardian orchestrator nlu dev-proxy || true

echo "⏳ Väntar på hälsa (via dev-proxy)…"
for i in {1..40}; do
  curl -fsS "$API_BASE/health" >/dev/null 2>&1 && break || sleep 1
done

echo "✅ Hälsa OK. Samlar basstatus…"
# Initial resource guard
resource_guard || true
# Start stage timer & reporter
STAGE_T0=$(sec_now)
LAST_REPORT=$STAGE_T0
# Mark test start timestamp (ISO)
START_TS_ISO=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
export START_TS_ISO
# Unique run prefixes for session ids
RUN_ID=$(date +%s%3N)
MICRO_PREFIX="auto-${RUN_ID}-"
PLANNER_PREFIX="planner-${RUN_ID}-"
export MICRO_PREFIX PLANNER_PREFIX
curl -fsS "$API_BASE/api/status/simple" -o "$ART_DIR/pre_status.json" || true
curl -fsS "$API_BASE/api/status/routes" -o "$ART_DIR/pre_routes.json" || true
curl -fsS "$API_BASE/api/status/guardian" -o "$ART_DIR/pre_guardian.json" || true

echo "🗣️  Skapar realistisk trafik (svenska)…"
if [ -z "$FOCUS_ROUTE" ] || [ "$FOCUS_ROUTE" = "micro" ]; then
  for i in $(seq 1 $MICRO_LOOPS); do
    # Throttle per-iteration if needed
    if [ $((i % LOAD_CHECK_EVERY)) -eq 0 ]; then resource_guard || true; watchdog_check || true; progress_report || true; fi
    if [ "$SAFETY_THROTTLED" -eq 1 ]; then sleep "$THROTTLE_SLEEP" || true; fi
    curl -fsS -X POST "$API_BASE/api/chat" -H 'Content-Type: application/json' -H 'Authorization: Bearer test-key-123' \
      -d '{"v":"1","session_id":"'"${MICRO_PREFIX}${i}"'","lang":"sv","message":"'"${MICRO_MESSAGE}"'"}' >/dev/null || true
  done
fi

# Generate planner-specific traffic (always generate; more if focus=planner)
if [ "$FOCUS_ROUTE" = "planner" ]; then
  PLANNER_LOOPS=$PLANNER_LOOPS_FOCUS
fi
for i in $(seq 1 $PLANNER_LOOPS); do
  if [ $((i % LOAD_CHECK_EVERY)) -eq 0 ]; then resource_guard || true; watchdog_check || true; progress_report || true; fi
  if [ "$SAFETY_THROTTLED" -eq 1 ]; then sleep "$THROTTLE_SLEEP" || true; fi
  curl -fsS -X POST "$API_BASE/api/chat" -H 'Content-Type: application/json' -H 'Authorization: Bearer test-key-123' \
    -d '{"v":"1","session_id":"'"${PLANNER_PREFIX}${i}"'","lang":"sv","message":"'"${PLANNER_MESSAGE}"'"}' >/dev/null || true
done

if [ "${SKIP_EVAL:-false}" = "true" ]; then
  echo "⏭️  Skippar eval-harness (SKIP_EVAL=true)"
else
  echo "🧪 Kör eval-harness v1 mot riktiga endpoints…"
  docker compose build eval >/dev/null 2>&1 || true
  docker compose run --rm eval || true
fi
test -f "$ART_DIR/results.jsonl" || touch "$ART_DIR/results.jsonl"

echo "📈 Hämtar P95 per route efter trafik…"
curl -fsS "$API_BASE/api/status/routes" -o "$ART_DIR/post_routes.json" || true

echo "⚡ Brownout-röktest (valfritt men aktiverat):"
if docker compose ps | grep -q loadgen; then
  docker compose run --rm loadgen || true
fi
# samla guardian-logg
if compgen -G "$TEL_DIR/*/guardian.jsonl" > /dev/null; then
  tail -n 200 $(ls -1t $TEL_DIR/*/guardian.jsonl | head -n1) > "$ART_DIR/guardian_tail.jsonl" || true
fi

echo "🧮 Enhanced SLO-validering med distribution analysis…"
# Export variables for Node process
export ART_DIR TEL_DIR SLO_FAST_P95 SLO_PLANNER_FULL_P95 SLO_DEEP_FULL_P95 \
  MIN_SAMPLES_PER_ROUTE MAX_TAIL_PERCENT MIN_SCHEMA_OK_RATE MAX_FALLBACK_RATE
node - <<'NODE'
const fs = require('fs');
const ART_DIR = process.env.ART_DIR || 'data/tests';
const TEL_DIR = process.env.TEL_DIR || 'data/telemetry';
const START_TS_ISO = process.env.START_TS_ISO;
const FOCUS_ROUTE = process.env.FOCUS_ROUTE || '';

function readJSON(p, d={}){ try{return JSON.parse(fs.readFileSync(p,'utf8'))}catch{ return d}}
function parseTs(iso){
  if(!iso) return NaN;
  // Normalize microseconds (6 digits) to milliseconds (3 digits) for JS Date
  const fixed = iso.replace(/\.(\d{3})\d+Z$/, '.$1Z');
  const t = Date.parse(fixed);
  return isNaN(t) ? Date.parse(iso) : t;
}

// Read telemetry data for detailed analysis
function analyzeTelemetryData() {
  const today = new Date().toISOString().split('T')[0];
  const telemetryFile = `${TEL_DIR}/${today}/events_${today}.jsonl`;
  
  if (!fs.existsSync(telemetryFile)) {
    return { error: 'No telemetry data found' };
  }
  
  const lines = fs.readFileSync(telemetryFile, 'utf8').trim().split('\n').filter(Boolean);
  let eventsOriginal = lines.map(line => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
  let events = eventsOriginal;
  
  // Filter events strictly to this run via session_id prefixes
  const MICRO_PREFIX = process.env.MICRO_PREFIX || '';
  const PLANNER_PREFIX = process.env.PLANNER_PREFIX || '';
  const prefixes = [MICRO_PREFIX, PLANNER_PREFIX].filter(Boolean);
  if (prefixes.length) {
    events = eventsOriginal.filter(e => typeof e.session_id === 'string' && prefixes.some(p => e.session_id.startsWith(p)));
  }
  
  // Separate by route
  const routeData = {};
  events.forEach(event => {
    const route = event.route || 'unknown';
    if (!routeData[route]) {
      routeData[route] = { latencies: [], schema_ok: 0, fallback_used: 0, total: 0 };
    }
    
    routeData[route].latencies.push(event.e2e_full_ms);
    routeData[route].total++;
    
    if (event.rag && event.rag.planner_schema_ok) {
      routeData[route].schema_ok++;
    }
    if (event.rag && event.rag.fallback_used) {
      routeData[route].fallback_used++;
    }
  });
  
  // Calculate percentiles and statistics
  const results = {};
  Object.keys(routeData).forEach(route => {
    const data = routeData[route];
    const latencies = data.latencies.sort((a, b) => a - b);
    
    if (latencies.length === 0) {
      results[route] = { error: 'No data' };
      return;
    }
    
    const p50 = latencies[Math.floor(latencies.length * 0.5)];
    const p90 = latencies[Math.floor(latencies.length * 0.9)];
    const p95 = latencies[Math.floor(latencies.length * 0.95)];
    const p99 = latencies[Math.floor(latencies.length * 0.99)];
    
    // Calculate tail metrics
    const tail1500ms = latencies.filter(l => l > 1500).length;
    const tailPercent = (tail1500ms / latencies.length) * 100;
    
    // Check for bimodality (if >=3% > 5×p50)
    const bimodalThreshold = p50 * 5;
    const bimodalCount = latencies.filter(l => l > bimodalThreshold).length;
    const bimodalPercent = (bimodalCount / latencies.length) * 100;
    const isBimodal = bimodalPercent >= 3;
    
    // Calculate schema and fallback rates
    const schemaOkRate = data.total > 0 ? (data.schema_ok / data.total) * 100 : 0;
    const fallbackRate = data.total > 0 ? (data.fallback_used / data.total) * 100 : 0;
    
    results[route] = {
      samples: latencies.length,
      p50_ms: p50,
      p90_ms: p90,
      p95_ms: p95,
      p99_ms: p99,
      tail_1500ms_count: tail1500ms,
      tail_1500ms_percent: tailPercent,
      bimodal: isBimodal,
      bimodal_percent: bimodalPercent,
      schema_ok_rate: schemaOkRate,
      fallback_rate: fallbackRate,
      min_latency: latencies[0],
      max_latency: latencies[latencies.length - 1],
      mean_latency: latencies.reduce((a, b) => a + b, 0) / latencies.length
    };
  });
  
  return results;
}

const postRoutes = readJSON(ART_DIR+'/post_routes.json', {});
const telemetryAnalysis = analyzeTelemetryData();

function ensureNonEmpty(obj){ return obj && Object.keys(obj).length>0 }
if(!ensureNonEmpty(telemetryAnalysis)){
  console.error('❌ No telemetry found after test start – failing to avoid false PASS');
  process.exit(1);
}

// SLO validation with enhanced checks
const SLO_FAST = parseInt(process.env.SLO_FAST_P95||'250',10);
const SLO_PLAN = parseInt(process.env.SLO_PLANNER_FULL_P95||'1500',10);
const SLO_DEEP = parseInt(process.env.SLO_DEEP_FULL_P95||'3000',10);
const MIN_SAMPLES = parseInt(process.env.MIN_SAMPLES_PER_ROUTE||'500',10);
const MAX_TAIL = parseFloat(process.env.MAX_TAIL_PERCENT||'1');
const MIN_SCHEMA = parseFloat(process.env.MIN_SCHEMA_OK_RATE||'99');
const MAX_FALLBACK = parseFloat(process.env.MAX_FALLBACK_RATE||'1');

let fails = [];
let warnings = [];

// Check each route (optionally focused)
Object.keys(telemetryAnalysis).forEach(route => {
  const data = telemetryAnalysis[route];
  if (FOCUS_ROUTE && route !== FOCUS_ROUTE) return; 
  
  if (route === 'error') {
    return; // Skip gating for error bucket
  }
  
  if (data.error) {
    fails.push(`${route}: ${data.error}`);
    return;
  }
  
  // Check minimum samples
  if (data.samples < MIN_SAMPLES) {
    fails.push(`${route}: Insufficient samples (${data.samples} < ${MIN_SAMPLES})`);
    return;
  }
  
  // Check P95 SLO
  const sloLimit = route === 'micro' ? SLO_FAST : route === 'planner' ? SLO_PLAN : SLO_DEEP;
  if (data.p95_ms > sloLimit) {
    fails.push(`${route} p95 ${data.p95_ms}ms > ${sloLimit}ms`);
  }
  
  // Check tail distribution
  if (data.tail_1500ms_percent > MAX_TAIL) {
    fails.push(`${route} tail >1.5s: ${data.tail_1500ms_percent.toFixed(1)}% > ${MAX_TAIL}%`);
  }
  
  // Check schema success rate
  if (route === 'planner' && data.schema_ok_rate < MIN_SCHEMA) {
    fails.push(`${route} schema_ok: ${data.schema_ok_rate.toFixed(1)}% < ${MIN_SCHEMA}%`);
  }
  
  // Check fallback rate
  if (data.fallback_rate > MAX_FALLBACK) {
    fails.push(`${route} fallback_used: ${data.fallback_rate.toFixed(1)}% > ${MAX_FALLBACK}%`);
  }
  
  // Warn about bimodality
  if (data.bimodal) {
    warnings.push(`${route}: Bimodal distribution detected (${data.bimodal_percent.toFixed(1)}% > 5×p50)`);
  }
});

const resLines = fs.existsSync(ART_DIR+'/results.jsonl')
  ? fs.readFileSync(ART_DIR+'/results.jsonl','utf8').trim().split('\n').filter(Boolean).map(line=>{ try { return JSON.parse(line) } catch { return null } }).filter(Boolean)
  : [];
const total = resLines.length;
const pass = resLines.filter(r=>r.ok).length;
const rate = total? Math.round(100*pass/total): 100;

const summary = {
  ts: new Date().toISOString(),
  slo: {
    fast_p95_ok: FOCUS_ROUTE && FOCUS_ROUTE !== 'micro' ? true : !fails.some(f => f.includes('micro')),
    planner_p95_ok: FOCUS_ROUTE && FOCUS_ROUTE !== 'planner' ? true : !fails.some(f => f.includes('planner')),
    deep_p95_ok: FOCUS_ROUTE && FOCUS_ROUTE !== 'deep' ? true : !fails.some(f => f.includes('deep'))
  },
  p95_ms: {
    fast: telemetryAnalysis.micro?.p95_ms,
    planner: telemetryAnalysis.planner?.p95_ms,
    deep: telemetryAnalysis.deep?.p95_ms
  },
  eval: {total, pass, rate_pct: rate},
  telemetry_analysis: telemetryAnalysis,
  fails,
  warnings,
  validation: {
    min_samples_met: Object.values(telemetryAnalysis).every(d => !d.error && d.samples >= MIN_SAMPLES),
    tail_distribution_ok: Object.values(telemetryAnalysis).every(d => !d.error && d.tail_1500ms_percent <= MAX_TAIL),
    schema_success_ok: Object.values(telemetryAnalysis).every(d => !d.error && (d.schema_ok_rate >= MIN_SCHEMA || d.schema_ok_rate === 0)),
    fallback_rate_ok: Object.values(telemetryAnalysis).every(d => !d.error && d.fallback_rate <= MAX_FALLBACK)
  }
};

fs.writeFileSync(ART_DIR+'/summary.json', JSON.stringify(summary,null,2));
fs.writeFileSync(ART_DIR+'/telemetry_analysis.json', JSON.stringify(telemetryAnalysis,null,2));

console.log(JSON.stringify(summary,null,2));

// Exit with error if any validation fails
if(fails.length > 0 || rate < 80){ 
  console.error('\n❌ VALIDATION FAILED:');
  fails.forEach(f => console.error('  - ' + f));
  if (warnings.length > 0) {
    console.error('\n⚠️  WARNINGS:');
    warnings.forEach(w => console.error('  - ' + w));
  }
  process.exit(1) 
}
NODE

echo "🎉 AUTO-VERIFY PASS. Sammanfattning finns i $ART_DIR/summary.json"
echo "📊 Detaljerad telemetry analysis finns i $ART_DIR/telemetry_analysis.json"

echo "📝 Uppdaterar styrdokument från artifacts…"
API_BASE="$API_BASE" ART_SUMMARY="$ART_DIR/summary.json" python3 scripts/update_docs_intelligent.py || true

echo "🪄 Kör curator för gårdagen…"
docker compose run --rm curator > "$ART_DIR/curator_summary.json" || true
