#!/usr/bin/env python3
import os, sys, re

ROOT = os.path.dirname(os.path.dirname(__file__))

SWEDISH_HINTS = [
    r"\b(med|och|eller|inte|ska|behövs|klara|nästa|steg|daglig|hastighet|svenska)\b",
    r"å", r"ä", r"ö"
]

ALLOW_PATHS = {
    os.path.join("docs","archive"),
}

def is_allowed(path: str) -> bool:
    return any(path.startswith(p) for p in ALLOW_PATHS)

def main():
    bad = []
    for dirpath,_,files in os.walk(ROOT):
        for f in files:
            if not f.endswith('.md'):
                continue
            rel = os.path.relpath(os.path.join(dirpath,f), ROOT)
            if is_allowed(rel):
                continue
            try:
                s = open(os.path.join(ROOT, rel), 'r', encoding='utf-8').read()
            except Exception:
                continue
            for hint in SWEDISH_HINTS:
                if re.search(hint, s, flags=re.IGNORECASE):
                    bad.append(rel)
                    break
    if bad:
        print("Non-English docs detected (Swedish hints):")
        for b in bad:
            print(" -", b)
        sys.exit(1)
    print("Docs language check passed (English only)")
    sys.exit(0)

if __name__ == '__main__':
    main()

