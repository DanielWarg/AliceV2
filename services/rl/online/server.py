#!/usr/bin/env python3
"""
Bandit HTTP Server för live routing decisions
Exponerar endpoints för pull/update/health
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.rl.online.linucb_router import LinUCBRouter
from services.rl.online.thompson_tools import ThompsonTools

# Environment configuration
BANDIT_PORT = int(os.getenv("BANDIT_PORT", "8850"))
BANDIT_TIMEOUT_MS = int(os.getenv("BANDIT_TIMEOUT_MS", "40"))
CANARY_SHARE = float(os.getenv("CANARY_SHARE", "0.05"))
BANDIT_FAIL_OPEN = os.getenv("BANDIT_FAIL_OPEN", "true").lower() in ("1", "true", "yes")

app = FastAPI(title="Alice RL Bandit Server", version="T5")

# Global bandit instances
router: Optional[LinUCBRouter] = None
tools: Optional[ThompsonTools] = None


class ContextFeatures(BaseModel):
    """Context features for routing decision"""

    intent_conf: float
    len_chars: int
    has_question: bool
    cache_hint: bool
    guardian_state: str
    prev_tool_error: bool


class RouteRequest(BaseModel):
    """Request for route selection"""

    context: ContextFeatures
    available_routes: Optional[list] = None


class ToolRequest(BaseModel):
    """Request for tool selection"""

    intent: str
    available_tools: Optional[list] = None


class UpdateRequest(BaseModel):
    """Request to update bandit with reward"""

    decision_type: str  # "route" or "tool"
    context: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    arm: str
    reward: float


class BanditResponse(BaseModel):
    """Response from bandit"""

    arm: str
    confidence: float
    method: str  # "bandit", "fallback", "guardian_override"
    timestamp: float


@app.on_event("startup")
async def startup():
    """Initialize bandit models"""
    global router, tools
    try:
        router = LinUCBRouter()
        tools = ThompsonTools()
        print(f"✅ Bandit server started on port {BANDIT_PORT}")
        print(
            f"📊 LinUCB: {len(router.state.arms)} arms, {sum(arm.pulls for arm in router.state.arms.values())} total pulls"
        )
        print(f"📊 Thompson: {len(tools.state.policies)} policies")
    except Exception as e:
        print(f"❌ Failed to initialize bandits: {e}")
        raise


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "router_arms": len(router.state.arms) if router else 0,
        "tool_policies": len(tools.state.policies) if tools else 0,
    }


@app.post("/bandit/route", response_model=BanditResponse)
async def select_route(request: RouteRequest):
    """Select routing arm using LinUCB"""
    start_time = time.time()

    try:
        # Guardian override: EMERGENCY state -> force micro
        if request.context.guardian_state == "EMERGENCY":
            return BanditResponse(
                arm="micro",
                confidence=1.0,
                method="guardian_override",
                timestamp=time.time(),
            )

        if not router:
            raise HTTPException(status_code=503, detail="Router not initialized")

        # Convert to dict for LinUCB
        context_dict = request.context.dict()

        # Select arm
        selected_arm = router.select(context_dict)

        # Calculate confidence (simplified)
        confidence = min(0.95, 0.5 + (router.state.arms[selected_arm].pulls / 1000.0))

        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms > BANDIT_TIMEOUT_MS:
            print(
                f"⚠️ Route selection timeout: {elapsed_ms:.1f}ms > {BANDIT_TIMEOUT_MS}ms"
            )

        return BanditResponse(
            arm=selected_arm,
            confidence=confidence,
            method="bandit",
            timestamp=time.time(),
        )

    except Exception as e:
        if BANDIT_FAIL_OPEN:
            # Fallback to safe default
            return BanditResponse(
                arm="micro", confidence=0.0, method="fallback", timestamp=time.time()
            )
        else:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/bandit/tool", response_model=BanditResponse)
async def select_tool(request: ToolRequest):
    """Select tool using Thompson Sampling"""
    start_time = time.time()

    try:
        if not tools:
            raise HTTPException(status_code=503, detail="Tools not initialized")

        # Select tool
        selected_tool = tools.select(request.intent, request.available_tools)

        if not selected_tool:
            if BANDIT_FAIL_OPEN:
                return BanditResponse(
                    arm="fallback_tool",
                    confidence=0.0,
                    method="fallback",
                    timestamp=time.time(),
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No tools available for intent: {request.intent}",
                )

        # Calculate confidence from Beta parameters
        policy = tools.state.policies.get(request.intent, {})
        if selected_tool in policy:
            arm = policy[selected_tool]
            confidence = arm.alpha / (arm.alpha + arm.beta)
        else:
            confidence = 0.5

        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms > BANDIT_TIMEOUT_MS:
            print(
                f"⚠️ Tool selection timeout: {elapsed_ms:.1f}ms > {BANDIT_TIMEOUT_MS}ms"
            )

        return BanditResponse(
            arm=selected_tool,
            confidence=confidence,
            method="bandit",
            timestamp=time.time(),
        )

    except Exception as e:
        if BANDIT_FAIL_OPEN:
            return BanditResponse(
                arm="fallback_tool",
                confidence=0.0,
                method="fallback",
                timestamp=time.time(),
            )
        else:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/bandit/update")
async def update_bandit(request: UpdateRequest):
    """Update bandit with reward feedback"""
    try:
        if request.decision_type == "route":
            if router:
                context_dict = request.context or {}
                router.update(context_dict, request.arm, request.reward)
        elif request.decision_type == "tool":
            if tools:
                tools.update(request.intent or "", request.arm, request.reward)

        return {"status": "updated", "timestamp": time.time()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bandit/stats")
async def get_stats():
    """Get bandit statistics"""
    stats = {
        "timestamp": time.time(),
        "config": {
            "canary_share": CANARY_SHARE,
            "timeout_ms": BANDIT_TIMEOUT_MS,
            "fail_open": BANDIT_FAIL_OPEN,
        },
    }

    if router:
        stats["router"] = {
            "arms": len(router.state.arms),
            "total_pulls": sum(arm.pulls for arm in router.state.arms.values()),
            "arm_stats": {
                name: {"pulls": arm.pulls, "reward_sum": arm.reward_sum}
                for name, arm in router.state.arms.items()
            },
        }

    if tools:
        stats["tools"] = {
            "policies": len(tools.state.policies),
            "total_intents": len(tools.state.policies),
            "policy_stats": {
                intent: {
                    "tools": len(policy),
                    "total_pulls": sum(arm.pulls for arm in policy.values()),
                }
                for intent, policy in tools.state.policies.items()
            },
        }

    return stats


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=BANDIT_PORT)
