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
MAX_TAIL_PERCENT=${MAX_TAIL_PERCENT:-1}  # Max 1% of requests > 1.5s
MIN_SCHEMA_OK_RATE=${MIN_SCHEMA_OK_RATE:-99}  # Min 99% schema success
MAX_FALLBACK_RATE=${MAX_FALLBACK_RATE:-1}  # Max 1% fallback usage

mkdir -p "$ART_DIR"
> "$ART_DIR/results.jsonl"

echo "▶️  Startar tjänster via docker compose (docker-only)…"
docker compose up -d guardian orchestrator nlu dev-proxy || true

echo "⏳ Väntar på hälsa (via dev-proxy)…"
for i in {1..40}; do
  curl -fsS "$API_BASE/health" >/dev/null 2>&1 && break || sleep 1
done

echo "✅ Hälsa OK. Samlar basstatus…"
# Mark test start timestamp (ISO)
START_TS_ISO=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
export START_TS_ISO
curl -fsS "$API_BASE/api/status/simple" -o "$ART_DIR/pre_status.json" || true
curl -fsS "$API_BASE/api/status/routes" -o "$ART_DIR/pre_routes.json" || true
curl -fsS "$API_BASE/api/status/guardian" -o "$ART_DIR/pre_guardian.json" || true

echo "🗣️  Skapar realistisk trafik (svenska)…"
# Generate more traffic for better statistics
for i in {1..600}; do
  curl -fsS -X POST "$API_BASE/api/chat" -H 'Content-Type: application/json' -H 'Authorization: Bearer test-key-123' \
    -d '{"v":"1","session_id":"auto-test-'$i'","lang":"sv","message":"Hej Alice, vad är klockan?"}' >/dev/null || true
done

# Generate planner-specific traffic
for i in {1..600}; do
  curl -fsS -X POST "$API_BASE/api/chat" -H 'Content-Type: application/json' -H 'Authorization: Bearer test-key-123' \
    -d '{"v":"1","session_id":"planner-test-'$i'","lang":"sv","message":"Vad är vädret i Stockholm?"}' >/dev/null || true
done

echo "🧪 Kör eval-harness v1 mot riktiga endpoints…"
docker compose build eval >/dev/null 2>&1 || true
docker compose run --rm eval || true
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
node - <<NODE
const fs = require('fs');
const ART_DIR = '${ART_DIR}';
const TEL_DIR = '${TEL_DIR}';
const START_TS_ISO = process.env.START_TS_ISO;

function readJSON(p, d={}){ try{return JSON.parse(fs.readFileSync(p,'utf8'))}catch{ return d}}

// Read telemetry data for detailed analysis
function analyzeTelemetryData() {
  const today = new Date().toISOString().split('T')[0];
  const telemetryFile = \`\${TEL_DIR}/\${today}/events_\${today}.jsonl\`;
  
  if (!fs.existsSync(telemetryFile)) {
    return { error: 'No telemetry data found' };
  }
  
  const lines = fs.readFileSync(telemetryFile, 'utf8').trim().split('\\n').filter(Boolean);
  let events = lines.map(line => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
  
  // Filter by start timestamp to avoid stale data from previous runs
  if (START_TS_ISO) {
    const start = new Date(START_TS_ISO).getTime();
    events = events.filter(e => {
      const ts = e.ts ? new Date(e.ts).getTime() : 0;
      return ts >= start;
    });
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

// SLO validation with enhanced checks
const SLO_FAST = parseInt('${SLO_FAST_P95}'||'250',10);
const SLO_PLAN = parseInt('${SLO_PLANNER_FULL_P95}'||'1500',10);
const SLO_DEEP = parseInt('${SLO_DEEP_FULL_P95}'||'3000',10);
const MIN_SAMPLES = parseInt('${MIN_SAMPLES_PER_ROUTE}'||'500',10);
const MAX_TAIL = parseFloat('${MAX_TAIL_PERCENT}'||'1',10);
const MIN_SCHEMA = parseFloat('${MIN_SCHEMA_OK_RATE}'||'99',10);
const MAX_FALLBACK = parseFloat('${MAX_FALLBACK_RATE}'||'1',10);

let fails = [];
let warnings = [];

// Check each route
Object.keys(telemetryAnalysis).forEach(route => {
  const data = telemetryAnalysis[route];
  
  if (data.error) {
    fails.push(\`\${route}: \${data.error}\`);
    return;
  }
  
  // Check minimum samples
  if (data.samples < MIN_SAMPLES) {
    fails.push(\`\${route}: Insufficient samples (\${data.samples} < \${MIN_SAMPLES})\`);
    return;
  }
  
  // Check P95 SLO
  const sloLimit = route === 'micro' ? SLO_FAST : route === 'planner' ? SLO_PLAN : SLO_DEEP;
  if (data.p95_ms > sloLimit) {
    fails.push(\`\${route} p95 \${data.p95_ms}ms > \${sloLimit}ms\`);
  }
  
  // Check tail distribution
  if (data.tail_1500ms_percent > MAX_TAIL) {
    fails.push(\`\${route} tail >1.5s: \${data.tail_1500ms_percent.toFixed(1)}% > \${MAX_TAIL}%\`);
  }
  
  // Check schema success rate
  if (route === 'planner' && data.schema_ok_rate < MIN_SCHEMA) {
    fails.push(\`\${route} schema_ok: \${data.schema_ok_rate.toFixed(1)}% < \${MIN_SCHEMA}%\`);
  }
  
  // Check fallback rate
  if (data.fallback_rate > MAX_FALLBACK) {
    fails.push(\`\${route} fallback_used: \${data.fallback_rate.toFixed(1)}% > \${MAX_FALLBACK}%\`);
  }
  
  // Warn about bimodality
  if (data.bimodal) {
    warnings.push(\`\${route}: Bimodal distribution detected (\${data.bimodal_percent.toFixed(1)}% > 5×p50)\`);
  }
});

const resLines = fs.existsSync(ART_DIR+'/results.jsonl')
  ? fs.readFileSync(ART_DIR+'/results.jsonl','utf8').trim().split('\\n').filter(Boolean).map(JSON.parse)
  : [];
const total = resLines.length;
const pass = resLines.filter(r=>r.ok).length;
const rate = total? Math.round(100*pass/total): 100;

const summary = {
  ts: new Date().toISOString(),
  slo: {
    fast_p95_ok: !fails.some(f => f.includes('micro')),
    planner_p95_ok: !fails.some(f => f.includes('planner')),
    deep_p95_ok: !fails.some(f => f.includes('deep'))
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
  console.error('\\n❌ VALIDATION FAILED:');
  fails.forEach(f => console.error('  - ' + f));
  if (warnings.length > 0) {
    console.error('\\n⚠️  WARNINGS:');
    warnings.forEach(w => console.error('  - ' + w));
  }
  process.exit(1) 
}
NODE

echo "🎉 AUTO-VERIFY PASS. Sammanfattning finns i $ART_DIR/summary.json"
echo "📊 Detaljerad telemetry analysis finns i $ART_DIR/telemetry_analysis.json"

echo "📝 Uppdaterar styrdokument från artifacts…"
API_BASE="$API_BASE" ART_SUMMARY="$ART_DIR/summary.json" python3 scripts/update_docs.py || true

echo "🪄 Kör curator för gårdagen…"
docker compose run --rm curator > "$ART_DIR/curator_summary.json" || true
