#!/usr/bin/env python3
import os, sys
"""
Rollback till baseline genom att nolla canary-andelen.
"""
ENV_FILE = ".env.canary"
def main():
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("PREFS_CANARY_SHARE=0.00\n")
    print("[rollback] Canary share satt till 0.00")
if __name__ == "__main__":
    main()