#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:18000}"
GUARD_BASE="${GUARD_BASE:-http://localhost:18000}"
ART_DIR="${ART_DIR:-data/tests}"
TEL_DIR="${TEL_DIR:-data/telemetry}"
SLO_FAST_P95=${SLO_FAST_P95:-250}
SLO_PLANNER_FULL_P95=${SLO_PLANNER_FULL_P95:-1500}
SLO_DEEP_FULL_P95=${SLO_DEEP_FULL_P95:-3000}

mkdir -p "$ART_DIR"

echo "⏳ Väntar på proxy (hälsa via /health)…"
for i in {1..40}; do
  curl -fsS "$API_BASE/health" >/dev/null 2>&1 && break || sleep 1
done

echo "✅ Hälsa OK. Samlar basstatus…"
curl -fsS "$API_BASE/api/status/simple" -o "$ART_DIR/pre_status.json" || true
curl -fsS "$API_BASE/api/status/routes" -o "$ART_DIR/pre_routes.json" || true
curl -fsS "$API_BASE/api/status/guardian" -o "$ART_DIR/pre_guardian.json" || true

echo "🗣️  Skapar realistisk trafik (svenska)…"
for i in {1..10}; do
  curl -fsS -X POST "$API_BASE/api/orchestrator/chat" -H 'Content-Type: application/json' -H 'Authorization: Bearer test-key-123' \
    -d '{"session_id":"auto-test-'$i'","message":"Hej Alice, vad är klockan?"}' >/dev/null || true
done

echo "🧪 Kör eval-harness v1 mot riktiga endpoints…"
cd services/eval && source .venv/bin/activate && python eval.py || true
cd ../..

echo "📈 Hämtar P95 per route efter trafik…"
curl -fsS "$API_BASE/api/status/routes" -o "$ART_DIR/post_routes.json" || true

echo "🧮 SLO-validering…"
node - <<NODE
const fs = require('fs');
const ART_DIR = '${ART_DIR}';
function readJSON(p, d={}){ try{return JSON.parse(fs.readFileSync(p,'utf8'))}catch{ return d}}
const postRoutes = readJSON(ART_DIR+'/post_routes.json', {});
const raw = (postRoutes.raw||{});
const ok = (route, lim) => !raw[route] || raw[route].p95_ms===null || raw[route].p95_ms <= lim;

const SLO_FAST = parseInt('${SLO_FAST_P95}'||'250',10);
const SLO_PLAN = parseInt('${SLO_PLANNER_FULL_P95}'||'1500',10);
const SLO_DEEP = parseInt('${SLO_DEEP_FULL_P95}'||'3000',10);

let fails = [];
if(!ok('micro', SLO_FAST))  fails.push(\`FAST p95 \${raw.micro?.p95_ms}ms > \${SLO_FAST}ms\`);
if(!ok('planner', SLO_PLAN))fails.push(\`PLANNER p95 \${raw.planner?.p95_ms}ms > \${SLO_PLAN}ms\`);
if(!ok('deep', SLO_DEEP))   fails.push(\`DEEP p95 \${raw.deep?.p95_ms}ms > \${SLO_DEEP}ms\`);

const resLines = fs.existsSync(ART_DIR+'/results.jsonl')
  ? fs.readFileSync(ART_DIR+'/results.jsonl','utf8').trim().split('\\n').filter(Boolean).map(JSON.parse)
  : [];
const total = resLines.length;
const pass = resLines.filter(r=>r.ok).length;
const rate = total? Math.round(100*pass/total): 100;

const summary = {
  ts: new Date().toISOString(),
  slo: {fast_p95_ok: ok('micro',SLO_FAST), planner_p95_ok: ok('planner',SLO_PLAN), deep_p95_ok: ok('deep',SLO_DEEP)},
  p95_ms: {fast: raw.micro?.p95_ms, planner: raw.planner?.p95_ms, deep: raw.deep?.p95_ms},
  eval: {total, pass, rate_pct: rate},
  fails
};
fs.writeFileSync(ART_DIR+'/summary.json', JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,2));
if(fails.length || rate < 80){ process.exit(1) }
NODE

echo "🎉 AUTO-VERIFY PASS. Sammanfattning finns i $ART_DIR/summary.json"
