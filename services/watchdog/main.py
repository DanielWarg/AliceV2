import os
import subprocess
import time

import httpx
import yaml
from github import Github
from prometheus_client import Counter, Gauge, start_http_server

CFG = yaml.safe_load(open("/app/config.yaml"))

g_up = Gauge("svc_up", "1=healthy,0=down", ["service"])
g_p95 = Gauge("svc_p95_ms", "p95 latency (ms)", ["route"])
g_tool = Gauge("tool_precision", "tool precision", [])
g_success = Gauge("success_rate", "success rate", [])
g_cache = Gauge("cache_hit_ratio", "cache hit rate", [])
c_crit = Counter("watchdog_critical_total", "critical incidents")


def curl_json(url, timeout=2.0):
    try:
        r = httpx.get(url, timeout=timeout)
        if r.status_code != 200:
            return r.status_code, None
        ct = r.headers.get("content-type", "")
        return r.status_code, (r.json() if "json" in ct else None)
    except Exception:
        return -1, None


def slack(msg: str):
    hook = os.getenv("SLACK_WEBHOOK_URL") or CFG["actions"].get("slack_webhook")
    if not hook:
        return
    try:
        httpx.post(hook, json={"text": msg}, timeout=2.0)
    except Exception:
        pass


def gh_status(state: str, description: str):
    token_env = CFG["actions"].get("github_token_env", "GITHUB_TOKEN")
    token = os.getenv(token_env, "")
    if not token:
        return
    repo_name = CFG["actions"]["github_repo"]
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        sha = repo.get_branch("main").commit.sha
        repo.get_commit(sha=sha).create_status(
            state=state, context="watchdog", description=description
        )
    except Exception:
        pass


def compose_restart(service: str):
    subprocess.run(["docker", "compose", "restart", service], check=False)


def evaluate(metrics):
    breaches = []
    slo = CFG["slo"]
    if metrics["p95"]["fast"] > slo["latency_p95_ms"]["fast"]:
        breaches.append(f"fast p95 {metrics['p95']['fast']}ms")
    if metrics["p95"]["planner_first"] > slo["latency_p95_ms"]["planner_first"]:
        breaches.append(f"planner_first p95 {metrics['p95']['planner_first']}ms")
    if metrics["p95"]["planner_full"] > slo["latency_p95_ms"]["planner_full"]:
        breaches.append(f"planner_full p95 {metrics['p95']['planner_full']}ms")
    if metrics["tool_precision"] < slo["tool_precision_min"]:
        breaches.append(f"tool_precision {metrics['tool_precision']:.2f}")
    if metrics["success_rate"] < slo["success_rate_min"]:
        breaches.append(f"success_rate {metrics['success_rate']:.2f}")
    if metrics["cache_hit"] < slo["cache_hit_min"]:
        breaches.append(f"cache_hit {metrics['cache_hit']:.2f}")
    return breaches


def main():
    start_http_server(int(CFG.get("prometheus_port", 9308)))
    crit_burst = 0
    burst_threshold = int(CFG["actions"].get("burst_threshold", 2))

    while True:
        unhealthy = []

        # health probes
        for name, url in CFG["endpoints"].items():
            code, _ = curl_json(url)
            g_up.labels(name).set(1 if code == 200 else 0)
            if code != 200:
                unhealthy.append((name, code))

        # hud snapshot för SLO
        code, hud = curl_json(CFG.get("hud_snapshot_url"))
        if code == 200 and isinstance(hud, dict):
            p95 = hud.get("p95", {"fast": 0, "planner_first": 0, "planner_full": 0})
            tool = float(hud.get("tool_precision", 0))
            succ = float(hud.get("success_rate", 0))
            cache = float(hud.get("cache_hit_ratio", 0))
        else:
            p95 = {"fast": 9999, "planner_first": 9999, "planner_full": 9999}
            tool = succ = cache = 0.0

        # export
        g_p95.labels("fast").set(p95["fast"])
        g_p95.labels("planner_first").set(p95["planner_first"])
        g_p95.labels("planner_full").set(p95["planner_full"])
        g_tool.set(tool)
        g_success.set(succ)
        g_cache.set(cache)

        breaches = evaluate(
            {
                "p95": p95,
                "tool_precision": tool,
                "success_rate": succ,
                "cache_hit": cache,
            }
        )

        if unhealthy or breaches:
            c_crit.inc()
            crit_burst += 1
            slack(f"⚠️ Watchdog: unhealthy={unhealthy} breaches={breaches}")

            # auto-restart sjuka containers (enkel & säker förstahjälp)
            for svc, _ in unhealthy:
                if svc in CFG["actions"].get("auto_restart_services", []):
                    compose_restart(svc)

            # repo freeze via commit-status
            if (
                CFG["actions"].get("freeze_on_critical_burst")
                and crit_burst >= burst_threshold
            ):
                gh_status("failure", "watchdog freeze: critical incidents")
        else:
            crit_burst = 0
            gh_status("success", "watchdog ok")

        time.sleep(int(CFG["poll_interval_s"]))


if __name__ == "__main__":
    main()
