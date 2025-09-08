#!/usr/bin/env python3
import json, os, time, statistics as st
from pathlib import Path

HIST = Path("data/ops/drift_history.jsonl")
RCA  = Path("data/ops/rca/reasons_hist.json")
OUT  = Path("ops/dashboards/dashboard.md")

def load_history(p: Path):
    rows=[]
    if not p.exists(): return rows
    with p.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                rows.append(json.loads(line))
            except: pass
    return rows

def load_rca(p: Path):
    if not p.exists(): return {"hist": {}, "top2": []}
    return json.loads(p.read_text(encoding="utf-8"))

def _fmt_ts(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts))

def kpis(rows):
    if not rows:
        return {"psi_avg": None, "psi_p95": None, "ks_avg": None, "ks_p95": None, "vf_avg": None, "vf_p95": None}
    def avg(xs): return round(sum(xs)/len(xs), 6) if xs else None
    def p95(xs):
        if not xs: return None
        xs = sorted(xs); idx = max(0, int(0.95*len(xs))-1); return round(xs[idx], 6)
    psi = [r["psi_intents"] for r in rows if "psi_intents" in r]
    ks  = [r["ks_length"] for r in rows if "ks_length" in r]
    vf  = [r["verifier_fail"] for r in rows if "verifier_fail" in r]
    return {
        "psi_avg": avg(psi), "psi_p95": p95(psi),
        "ks_avg":  avg(ks),  "ks_p95":  p95(ks),
        "vf_avg":  avg(vf),  "vf_p95":  p95(vf),
    }

def mermaid_line(title, xs, ys, ylabel):
    # xs: list of labels (strings), ys: list of floats
    if not xs or not ys:
        return f"**{title}**\n\n_Ingen data än._\n"
    # Mermaid line chart via 'plot' syntax (GitHub/GitLab stöder mermaid >=10)
    # Vi samplar max 120 punkter för läsbarhet
    if len(xs) > 120:
        step = len(xs)//120 + 1
        xs = xs[::step]; ys = ys[::step]
    series = ", ".join(str(round(v,6)) for v in ys)
    labels = ", ".join(xs)
    return f"""### {title}

```mermaid
%%{{init: {{'theme': 'base'}} }}%%
xychart-v2
    title "{title}"
    x-axis [{', '.join(f'"{x}"' for x in xs)}]
    y-axis "{ylabel}"
    line [{series}]
```

"""

def main():
    rows = load_history(HIST)
    rca = load_rca(RCA)
    
    xs = [ _fmt_ts(r["ts"]) for r in rows if "ts" in r ]
    psi = [ r["psi_intents"] for r in rows if "psi_intents" in r ]
    ks  = [ r["ks_length"] for r in rows if "ks_length" in r ]
    vf  = [ r["verifier_fail"] for r in rows if "verifier_fail" in r ]
    
    k = kpis(rows)
    
    # KPI-tabell
    kpi_md = f"""# Alice v2 — T8 Drift Dashboard

Uppdaterad: {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}

## KPI (rolling history)
| Metrik | Medel | P95 | Gate |
|--------|-------|-----|------|
| PSI (intents) | {k['psi_avg']} | {k['psi_p95']} | ≤ 0.20 |
| KS (längd) | {k['ks_avg']} | {k['ks_p95']} | ≤ 0.20 |
| Verifier fail | {k['vf_avg']} | {k['vf_p95']} | ≤ 0.01 |

"""
    
    # Grafer
    g1 = mermaid_line("PSI — Intent Drift", xs, psi, "PSI")
    g2 = mermaid_line("KS — Svarslängd", xs, ks, "KS")
    g3 = mermaid_line("Verifier Fail", xs, vf, "Fail-andel")
    
    # Top RCA orsaker
    top_rca = ""
    ordered = sorted((rca.get("hist") or {}).items(), key=lambda x:x[1], reverse=True)[:5]
    if ordered:
        top_rca = "## Topporsaker (RCA)\n" + "\n".join([f"- {k}: {v}" for k,v in ordered]) + "\n"
    else:
        top_rca = "## Topporsaker (RCA)\n- (Ingen RCA ännu)\n"
    
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(kpi_md + g1 + g2 + g3 + "\n" + top_rca, encoding="utf-8")
    print(f"[dashboard] wrote {OUT}")

if __name__ == "__main__":
    main()