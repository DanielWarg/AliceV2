import json, os
from pathlib import Path
from ops.scripts.ingest_prod_telemetry import _detect_intent

def test_detect_intent_fallback():
    cfg = {"intent_regex":{"time":[r"\bklockan\b"]}}
    assert _detect_intent("Vad är klockan nu?", cfg) == "time"

def test_window_output_schema(tmp_path, monkeypatch):
    # skapa liten NDJSON
    p = tmp_path/"prod_responses.ndjson"
    rows = [
        {"prompt":"Hej","answer":"Svar åäö","verifier_ok":True,"latency_ms":420,"route":"baseline","intent":"qa"},
        {"prompt":"Vädret?","answer":"Det är 20 grader.","verifier_ok":False,"latency_ms":510,"route":"canary","intent":"weather"}
    ]
    with p.open("w",encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")

    # minimal config override
    cfg = {
        "window":{"lookback_hours": 999, "max_events": 1000, "min_events": 1},
        "sources":[{"type":"file","path":str(p)}],
        "fields":{"prompt":"prompt","answer":"answer","intent":"intent","verifier_ok":"verifier_ok","latency_ms":"latency_ms","route":"route"},
        "intent_regex":{"qa":[r"."],"weather":[r"grader"]}
    }
    cfgp = tmp_path/"telemetry_sources.yaml"
    import yaml
    with cfgp.open("w",encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True)

    # point loader to our cfg
    import ops.scripts.ingest_prod_telemetry as ing
    def load_cfg_local():
        import yaml, json
        with open(cfgp,"r",encoding="utf-8") as ff:
            return yaml.safe_load(ff)
    ing.load_cfg = load_cfg_local

    outp = tmp_path/"telemetry_window.json"
    os.system(f"python -c \"import ops.scripts.ingest_prod_telemetry as m; m.main()\"")  # runs with default paths; skip
    # manual call:
    from ops.scripts.ingest_prod_telemetry import main as _main
    import sys
    sys.argv = ["ingest_prod_telemetry.py","--out",str(outp)]
    _main()

    assert outp.exists()
    data = json.loads(outp.read_text(encoding="utf-8"))
    assert "length_chars" in data and isinstance(data["length_chars"], list)
    assert "intent_hist_actual" in data and len(data["intent_hist_actual"]) == 7
    assert any(isinstance(x,bool) for x in data.get("verifier_ok",[]))