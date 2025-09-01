#!/usr/bin/env python3
import os, json, re, requests, sys

API_BASE = os.getenv("API_BASE", "http://localhost:18000")
ART_SUMMARY = os.getenv("ART_SUMMARY", "data/tests/summary.json")

def read_summary(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def get_routes(api: str) -> dict:
    try:
        r = requests.get(f"{api}/api/status/routes", timeout=3)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

def replace_line(content: str, pattern: str, new_line: str) -> str:
    lines = content.splitlines()
    out = []
    replaced = False
    rx = re.compile(pattern)
    for line in lines:
        if rx.search(line) and not replaced:
            out.append(new_line)
            replaced = True
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if content.endswith("\n") else "")

def update_readme(summary: dict) -> None:
    p = "README.md"
    try:
        with open(p, 'r', encoding='utf-8') as f:
            s = f.read()
        rate = summary.get('eval',{}).get('rate_pct')
        fast = summary.get('p95_ms',{}).get('fast')
        plan = summary.get('p95_ms',{}).get('planner')
        badge = f"> **🚀 Production Status**: Auto-verify PASS {rate}% | P95 fast={fast:.0f}ms planner={plan:.0f}ms"
        s = replace_line(s, r"^> \*\*🚀 Production Status\*\*:.*$", badge)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(s)
    except Exception:
        pass

def update_roadmap(summary: dict) -> None:
    p = "ROADMAP.md"
    try:
        with open(p, 'r', encoding='utf-8') as f:
            s = f.read()
        curr = "## 🚦 Live Milestone Tracker"
        if curr not in s:
            return
        rate = summary.get('eval',{}).get('rate_pct')
        fast_ok = summary.get('slo',{}).get('fast_p95_ok')
        plan_ok = summary.get('slo',{}).get('planner_p95_ok')
        tag = f"**Auto-verify**: PASS {rate}% | Fast P95 OK={fast_ok} | Planner P95 OK={plan_ok}"
        s = replace_line(s, r"^\*\*🚀 CURRENT STATUS\*\*:.*$", "**🚀 CURRENT STATUS**: " + tag)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(s)
    except Exception:
        pass

def update_agents(summary: dict) -> None:
    p = "AGENTS.md"
    try:
        with open(p, 'r', encoding='utf-8') as f:
            s = f.read()
        s = replace_line(s, r"^## 🚀 \*\*CURRENT PROJECT STATUS.*$", "## 🚀 **CURRENT PROJECT STATUS (Updated {})**".format(os.getenv('DOCS_DATE','2025-09-01')))
        with open(p, 'w', encoding='utf-8') as f:
            f.write(s)
    except Exception:
        pass

def main():
    summary = read_summary(ART_SUMMARY)
    routes = get_routes(API_BASE)
    # If summary empty, exit gracefully
    if not summary:
        print("No summary.json; skipping docs update")
        return 0
    update_readme(summary)
    update_roadmap(summary)
    update_agents(summary)
    print("Docs updated from artifacts.")
    return 0

if __name__ == "__main__":
    sys.exit(main())


