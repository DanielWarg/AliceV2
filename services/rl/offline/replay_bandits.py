# services/rl/offline/replay_bandits.py
# Kör offline replay på datasetet och tränar LinUCB + Thompson, med persistens.
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, Iterable

from services.rl.online.routing_linucb import LinUCBRouter, features_from_episode
from services.rl.online.tool_thompson import ThompsonToolSelector


def read_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="data/rl/v1/train.jsonl")
    ap.add_argument("--val", default="data/rl/v1/val.jsonl")
    ap.add_argument("--linucb_out", default="services/rl/weights/bandits/linucb.json")
    ap.add_argument("--thompson_out", default="services/rl/weights/bandits/thompson.json")
    args = ap.parse_args()

    train_path = Path(args.train)
    val_path = Path(args.val)

    # Ladda befintlig state om finns
    linucb = LinUCBRouter.load(args.linucb_out)
    thomp = ThompsonToolSelector.load(args.thompson_out)

    train_rewards = []
    n = 0
    for ep in read_jsonl(train_path):
        # Uppdatera LinUCB
        linucb.update_from_episode(ep)
        # Uppdatera Thompson (intent→tool)
        thomp.update_from_episode(ep)
        r = (ep.get("reward_components") or {}).get("total")
        if r is not None:
            train_rewards.append(float(r))
        n += 1

    # Validering (enkel medelreward)
    val_rewards = []
    m = 0
    for ep in read_jsonl(val_path):
        r = (ep.get("reward_components") or {}).get("total")
        if r is not None:
            val_rewards.append(float(r))
        m += 1

    avg_train = sum(train_rewards) / max(1, len(train_rewards))
    avg_val = sum(val_rewards) / max(1, len(val_rewards))

    print(f"[Replay] episodes(train)={n}, episodes(val)={m}")
    print(f"[Replay] avg_reward(train)={avg_train:.4f}, avg_reward(val)={avg_val:.4f}")

    # Persistens
    Path(args.linucb_out).parent.mkdir(parents=True, exist_ok=True)
    linucb.save(args.linucb_out)
    Path(args.thompson_out).parent.mkdir(parents=True, exist_ok=True)
    thomp.save(args.thompson_out)

    print(f"[Replay] saved LinUCB → {args.linucb_out}")
    print(f"[Replay] saved Thompson → {args.thompson_out}")


if __name__ == "__main__":
    main()