#!/usr/bin/env python3
"""
Intent Tuner: analyserar PSI-bidrag per intent och simulerar nya regex-uppsättningar
utan att röra prod-konfig. Skriver förslag till ops/suggestions/intent_tuning.*
"""
import json, re, argparse
from pathlib import Path
INTENTS = ["time","weather","email","summary","qa","chitchat","hard","code","finance","travel","other"]

def psi(exp, act, eps=1e-12):
    from math import log
    E=sum(exp) or 1; A=sum(act) or 1
    s=0.0
    for e,a in zip(exp,act):
        p=max(e/E,eps); q=max(a/A,eps); s += (q-p)*log(q/p)
    return s

def load_window(p="data/ops/telemetry_window.json"):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def _compile_map(rx_map):
    comp={}
    for k, arr in rx_map.items():
        comp[k]=[re.compile(pat, re.I) for pat in arr]
    return comp

def classify(text, cmap, priority):
    for bucket in priority:
        for r in cmap.get(bucket,[]):
            if r.search(text): return bucket
    return "other"

def simulate(new_regex_yaml="ops/suggestions/intent_regex_suggestions.yaml", window="data/ops/telemetry_window.json"):
    import yaml
    win = load_window(window)
    # bygg text-proxy (endast för klassning – inga rådata i fil)
    # vi har inte råtext i telemetry_window.json → använd *maskade RCA samples* om finns, annars hoppa simulering
    rca_path = Path("data/ops/rca/fail_samples.jsonl")
    texts=[]
    if rca_path.exists():
        for line in rca_path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try:
                ex=json.loads(line); texts.append(ex.get("snippet_redacted",""))
            except: pass
    # om inga maskade snippets finns, använd bucketsimulering: flytta procent från "unknown"->förslag
    with open(new_regex_yaml,"r",encoding="utf-8") as f:
        rx_map = yaml.safe_load(f) or {}

    priority = ["code","finance","travel","time","weather","email","summary","qa","chitchat","hard"]
    cmap = _compile_map(rx_map)

    # baseline
    base = win.get("intent_hist_baseline",[1,1,1])
    act = win.get("intent_hist_actual",[1,1,1])
    # kartlägg indexer
    # Om längderna skiljer, pad till INTENTS
    def pad(vec):
        if len(vec)>=len(INTENTS): return vec[:len(INTENTS)]
        return vec + [0]*(len(INTENTS)-len(vec))
    base = pad(base); act = pad(act)

    # heuristisk omfördelning: anta att "other/unknown" motsvarar sista element om saknas
    # (bättre: använd riktiga samples i texts och klassificera om)
    sim_act = act[:]
    if texts:
        # räkna om fördelning från maskade snippets
        sim_hist = {k:0 for k in INTENTS}
        for t in texts:
            b = classify(t, cmap, priority)
            sim_hist[b]+=1
        # proportionalt justera en del av act till sim_hist (t.ex. 20% av volymen som felmappats)
        k_act = sum(sim_act) or 1
        shift = int(0.2*k_act)
        # nudge: flytta 'qa' andel -> sim buckets
        qa_idx = INTENTS.index("qa")
        taken = min(shift, sim_act[qa_idx])
        sim_act[qa_idx] -= taken
        per = taken / max(1,sum(sim_hist.values()))
        for b,cnt in sim_hist.items():
            if cnt<=0: continue
            sim_act[INTENTS.index(b)] += int(cnt*per)
    # räkna PSI
    base_cut = base[:len(INTENTS)]; act_cut = act[:len(INTENTS)]; sim_cut = sim_act[:len(INTENTS)]
    from math import isfinite
    psi_now = psi(base_cut, act_cut)
    psi_sim = psi(base_cut, sim_cut)
    out = {
        "psi_now": round(psi_now,6),
        "psi_sim": round(psi_sim,6),
        "delta": round(psi_sim-psi_now,6),
        "intents": INTENTS,
        "base": base_cut,
        "actual": act_cut,
        "simulated": sim_cut
    }
    Path("ops/suggestions/intent_tuning.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate", action="store_true")
    args = ap.parse_args()
    if args.simulate:
        simulate()
    else:
        win = load_window()
        print(json.dumps({
            "intents": INTENTS,
            "base": win.get("intent_hist_baseline"),
            "actual": win.get("intent_hist_actual")
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()