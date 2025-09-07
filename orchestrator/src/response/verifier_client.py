#!/usr/bin/env python3
import json
import os
import subprocess
import sys

CFG = os.environ.get("PREFS_CFG", "services/rl/prefs/config_prefs.yaml")


def verify_text(text: str):
    cmd = [
        sys.executable,
        "services/rl/verifier/response_verifier.py",
        "--text",
        text,
        "--cfg",
        CFG,
    ]
    out = subprocess.check_output(cmd)
    return json.loads(out.decode("utf-8"))


def self_correct(text: str, hint: str):
    cmd = [
        sys.executable,
        "services/rl/verifier/self_correction.py",
        "--text",
        text,
        "--hint",
        hint,
        "--cfg",
        CFG,
    ]
    out = subprocess.check_output(cmd)
    return json.loads(out.decode("utf-8"))["text"]
