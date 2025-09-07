#!/usr/bin/env python3
# Lightweight stub for DPO/ORPO so pipeline always runs locally/CI.

import json, argparse, os, hashlib, time, random

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cfg", default="services/rl/prefs/config_prefs.yaml")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    n = 0
    agrees = 0
    rnd = random.Random(42)

    with open(args.data, "r", encoding="utf-8") as f:
        for line in f:
            ex = json.loads(line)
            n += 1
            agrees += 1 if ex.get("win_label") in ("A","B") else 0

    win_rate = agrees / max(1, n)
    adapter_path = os.path.join(args.out, "adapter.safetensors")
    payload = f"FAKE_ADAPTER\nwin_rate={win_rate}\nseed=42\n"
    with open(adapter_path, "wb") as f:
        f.write(payload.encode("utf-8"))
    
    manifest = {
        "created": int(time.time()),
        "pairs": n,
        "val_win_rate": round(win_rate, 3),
        "hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "lora": {"r": 13, "alpha": 16, "dropout": 0.05}
    }
    
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)
    
    print(f"[train_dpo] pairs={n} val_win_rate={manifest['val_win_rate']} → {adapter_path}")

if __name__ == "__main__":
    main()