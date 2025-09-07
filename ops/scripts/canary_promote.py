#!/usr/bin/env python3
import json
import os
import sys

"""
Promote canary från 5% → 20% om kriterier uppfylls.
I produktion ska detta läsa real telemetri. Här används en enkel gate via report.json.
"""
REPORT = "data/rl/prefs/v1/report.json"
ENV_FILE = ".env.canary"


def main():
    if not os.path.exists(REPORT):
        print("[promote] report saknas:", REPORT)
        sys.exit(1)
    rep = json.load(open(REPORT, "r", encoding="utf-8"))
    win = rep.get("win_rate", 0.0)
    hall = rep.get("hallucination_rate", 1.0)
    p95 = rep.get("p95_latency", 99.9)
    if win >= 0.70 and hall <= 0.005 and p95 <= 1.0:
        share = 0.20
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"PREFS_CANARY_SHARE={share}\n")
        print(f"[promote] Canary share uppdaterad till {share}")
        sys.exit(0)
    print(f"[promote] Kriterier ej uppfyllda (win={win}, hall={hall}, p95={p95})")
    sys.exit(2)


if __name__ == "__main__":
    main()
