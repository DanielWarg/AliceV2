# services/rl/pipelines/build_episodes.py
from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from pydantic import ValidationError

from services.rl.pipelines.dataset_schemas import (
    Action,
    Episode,
    Outcome,
    RawEvent,
    RewardComponents,
    State,
)
from services.rl.pipelines.utils_io import (
    canonical_key,
    iter_jsonl,
    mask_pii,
    write_jsonl,
)
from services.rl.rewards.reward_shaping import compute_reward_total

DEFAULT_SEED = 20250907


def event_to_episode(ev: Dict[str, Any]) -> Episode | None:
    """
    Mappar ett RawEvent → Episode. Inga φ-belöningar här (T3).
    Returnerar None om eventet inte går att validera.
    """
    # Map telemetry schema to RawEvent schema
    mapped_event = {
        "timestamp": ev.get("ts", ""),
        "session_id": ev.get("session_id", ""),
        "text": ev.get("input_text", ""),
        "intent": ev.get("route"),  # "planner", "chat", etc.
        "tool_called": None,  # Will extract from tool_calls if present
        "tool_success": None,  # Not in current telemetry format
        "latency_ms": ev.get("e2e_full_ms"),
        "energy_wh": ev.get("energy_wh"),
        "policy_refusal": False,  # Not in current telemetry format
        "extra": ev,  # Store original telemetry
    }

    # Extract tool info from tool_calls array if present
    tool_calls = ev.get("tool_calls", [])
    if tool_calls:
        mapped_event["tool_called"] = tool_calls[0].get("name")

    try:
        raw = RawEvent(**mapped_event)
    except ValidationError:
        return None

    text_masked = mask_pii(raw.text or "")
    features: Dict[str, Any] = {
        "len_chars": len(text_masked),
        "has_question": "?" in (raw.text or ""),
        "intent_conf": raw.extra.get("intent_conf", None),
        "route_hint": raw.extra.get("route_hint", None),
        "guardian_state": raw.extra.get("guardian_state", None),
        "cache_hit": raw.extra.get("cache_hit", None),
    }

    state = State(
        intent=raw.intent,
        text=text_masked,
        features=features,
    )
    action = Action(tool=raw.tool_called)
    outcome = Outcome(
        success=raw.tool_success,
        latency_ms=raw.latency_ms,
        energy_wh=raw.energy_wh,
    )

    # Beräkna φ-belöning (v1)
    comps, total = compute_reward_total(
        tool_success=raw.tool_success,
        latency_ms=raw.latency_ms,
        energy_wh=raw.energy_wh,
        safety_ok=(not raw.policy_refusal),
        features=features,
        # valfritt: alpha=None → env RL_ALPHA används, route_hint styr latency-target
    )

    rc = RewardComponents(
        precision=comps["precision"],
        latency=comps["latency"],
        energy=comps["energy"],
        safety=comps["safety"],
        total=total,
    )

    meta = {
        "timestamp": raw.timestamp,
        "session_id": raw.session_id,
        "policy_refusal": raw.policy_refusal,
        "canonical_key": canonical_key(text_masked, raw.intent, raw.tool_called),
        "raw_extra": raw.extra,
    }

    try:
        ep = Episode(
            state=state,
            action=action,
            outcome=outcome,
            reward_components=rc,
            meta=meta,
        )
        return ep
    except ValidationError:
        return None


def load_events(src_dir: Path) -> Iterable[Dict[str, Any]]:
    for p in sorted(src_dir.glob("*.jsonl")):
        for row in iter_jsonl(p):
            yield row


def split_dataset(
    episodes: List[Episode],
    seed: int = DEFAULT_SEED,
    ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
) -> Tuple[List[Episode], List[Episode], List[Episode]]:
    assert abs(sum(ratios) - 1.0) < 1e-6, "ratios must sum to 1.0"
    random.Random(seed).shuffle(episodes)
    n = len(episodes)
    n_train = int(n * ratios[0])
    n_val = int(n * ratios[1])
    train = episodes[:n_train]
    val = episodes[n_train : n_train + n_val]
    test = episodes[n_train + n_val :]
    return train, val, test


def episode_to_row(ep: Episode) -> Dict[str, Any]:
    # Platt JSONL-rad (stabilt schema för träning)
    return {
        "state": {
            "intent": ep.state.intent,
            "text": ep.state.text,
            "features": ep.state.features,
        },
        "action": {"tool": ep.action.tool},
        "outcome": {
            "success": ep.outcome.success,
            "latency_ms": ep.outcome.latency_ms,
            "energy_wh": ep.outcome.energy_wh,
        },
        "reward_components": {
            "precision": ep.reward_components.precision,
            "latency": ep.reward_components.latency,
            "energy": ep.reward_components.energy,
            "safety": ep.reward_components.safety,
            "total": ep.reward_components.total,
        },
        "meta": ep.meta,
    }


def build_episodes(
    src_dir: Path,
    out_dir: Path,
    seed: int = DEFAULT_SEED,
    ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
) -> Dict[str, int]:
    raw_events = list(load_events(src_dir))
    episodes: List[Episode] = []
    seen_keys: set[str] = set()

    for ev in raw_events:
        ep = event_to_episode(ev)
        if ep is None:
            continue
        ck = ep.meta.get("canonical_key")
        if ck in seen_keys:
            continue  # dedupe
        seen_keys.add(ck)
        episodes.append(ep)

    train, val, test = split_dataset(episodes, seed=seed, ratios=ratios)

    write_jsonl(out_dir / "train.jsonl", (episode_to_row(e) for e in train))
    write_jsonl(out_dir / "val.jsonl", (episode_to_row(e) for e in val))
    write_jsonl(out_dir / "test.jsonl", (episode_to_row(e) for e in test))

    return {
        "episodes": len(episodes),
        "train": len(train),
        "val": len(val),
        "test": len(test),
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Build RL episodes from telemetry")
    ap.add_argument("--src", type=Path, default=Path("data/telemetry"))
    ap.add_argument("--out", type=Path, default=Path("data/rl/v1"))
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--ratios", type=float, nargs=3, default=(0.8, 0.1, 0.1))
    args = ap.parse_args()

    stats = build_episodes(
        args.src, args.out, seed=args.seed, ratios=tuple(args.ratios)
    )
    print(f"[build_episodes] done: {stats}")
