#!/usr/bin/env python3
def allow_online_adaptation(metrics):
    # metrics: dict with verifier_fail, policy_breach, p95_delta
    return (metrics.get("policy_breach",0)==0 and
            metrics.get("verifier_fail",1.0)<=0.01 and
            metrics.get("p95_delta",0.0) <= 0.10)