#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import datetime
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

random.seed(43)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PNR_RE = re.compile(
    r"\b(?:19|20)?\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[- ]?\d{4}\b"
)
PHONE_RE = re.compile(r"\b(?:\+46|0)\d[\d\s-]{6,}\d\b")
ID_RE = re.compile(
    r"\b(?:ticket|case|ärende|id|ref|reference)\s*[:#]?\s*[A-Za-z0-9-]{5,}\b", re.I
)


def pii_mask(s: str) -> Tuple[str, bool]:
    before = s
    s = EMAIL_RE.sub("[MASK_EMAIL]", s)
    s = PNR_RE.sub("[MASK_PNR]", s)
    s = PHONE_RE.sub("[MASK_PHONE]", s)
    s = ID_RE.sub("[MASK_ID]", s)
    return s, (s != before)


def now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def length_bucket(text: str) -> str:
    n = len(text.split())
    if n <= 120:
        return "S"
    if n <= 512:
        return "M"
    return "L"


# Slot-vokabulärer för variation

APPS = [
    "webbportalen",
    "iOS-appen",
    "Android-appen",
    "skrivbordsklienten",
    "beta-klienten",
]
ACTIONS = [
    "exportera rapport",
    "logga in",
    "synka kunddata",
    "köra fakturering",
    "skicka e-postnotiser",
]
ERRORS = ["krasch", "felkod 503", "timeout", "fryser", "tappad anslutning"]
AREAS = ["fakturor", "biljetter", "kundregistret", "rapporter", "SLA-panelen"]
DUR = ["idag", "sedan igår", "sedan uppdateringen", "den här veckan", "sporadiskt"]
MEET_TYPES = [
    "kundmöte",
    "sprintdemo",
    "onboarding-genomgång",
    "avstämning",
    "incidentreview",
]
RISKS = [
    "dataförlust",
    "fördröjd onboarding",
    "dubbeldebitering",
    "SLA-miss",
    "compliance-risk",
]
DECISIONS = [
    "rulla tillbaka patch",
    "höja loggnivå",
    "prioritera bugg",
    "uppdatera rutin",
    "eskalera till devops",
]


def support_prompt():
    app = random.choice(APPS)
    action = random.choice(ACTIONS)
    err = random.choice(ERRORS)
    area = random.choice(AREAS)
    dur = random.choice(DUR)
    p = (
        f"Hej support,\n\nI {app} kan jag inte {action} – får {err}. "
        f"Det påverkar {area} {dur}. Ärende [MASK_ID]. Kan ni hjälpa?\n\nTack!"
    )
    return pii_mask(p)[0]


def meeting_prompt():
    mtype = random.choice(MEET_TYPES)
    d1, d2 = random.sample(DECISIONS, 2)
    r1, r2, r3 = random.sample(RISKS, 3)
    p = (
        f"Sammanfatta ett {mtype} med två beslut ({d1}, {d2}) och tre risker ({r1}, {r2}, {r3}). "
        f"Inkludera åtgärder, ansvariga och deadlines."
    )
    return p


def qa_prompt():
    area = random.choice(AREAS)
    p = (
        f"Hur gör jag för att felsöka problem i {area} utan att kontakta supporten? "
        f"Beskriv steg-för-steg och tips."
    )
    return p


def chosen_for(domain: str) -> str:
    if domain == "support_email":
        steps = [
            "Starta om klienten",
            "Kontrollera nätverksstatus",
            "Prova åtgärden i en mindre dataset",
            "Töm cache och logga in igen",
            "Verifiera behörigheter",
        ]
        picked = ", ".join(random.sample(steps, 3))
        return (
            f"Hej!\n\nTack för din rapport. Gör så här: {picked}. "
            f"Om felet kvarstår: svara med tidsstämpel, versionsinfo och [MASK_ID] så tar vi ärendet vidare.\n\nMvh Supporten"
        )
    if domain == "meeting_summary":
        return (
            "Sammanfattning:\n- Beslut: två åtgärder godkändes\n- Risker: tre identifierade\n"
            "- Åtgärder: tilldela ansvariga och deadlines\n- Nästa steg: följ upp i nästa möte"
        )
    return (
        "Gör så här:\n1) Öppna Inställningar → Säkerhet\n2) Välj 'Felsök' och kör guidens steg\n"
        "Tips: aktivera 2FA och dokumentera utfallet"
    )


def rejected_for(domain: str) -> str:
    if domain == "support_email":
        return "Prova igen senare."
    if domain == "meeting_summary":
        return "Vi hade möte."
    return "Testa lite olika saker."


def row(domain: str, prompt: str) -> Dict[str, Any]:
    chosen = rejected = ""
    if domain == "support_email":
        chosen = chosen_for(domain)
        rejected = rejected_for(domain)
    elif domain == "meeting_summary":
        chosen = chosen_for(domain)
        rejected = rejected_for(domain)
    else:
        chosen = chosen_for("qa")
        rejected = rejected_for("qa")
    _, cm = pii_mask(chosen)
    _, rm = pii_mask(rejected)
    return {
        "id": str(uuid.uuid4()),
        "domain": domain,
        "lang": "sv",
        "length_bucket": length_bucket(prompt + " " + chosen),
        "prompt": prompt.strip(),
        "chosen": chosen.strip(),
        "rejected": rejected.strip(),
        "source": "synth_sv",
        "judge": "rule_based_v2",
        "pii_masked": cm or rm,
        "quality_score": 3,
        "created_at": now_iso(),
    }


def make_rows(n_support: int, n_meeting: int, n_qa: int) -> List[Dict[str, Any]]:
    rows = []
    for _ in range(n_support):
        rows.append(row("support_email", support_prompt()))
    for _ in range(n_meeting):
        rows.append(row("meeting_summary", meeting_prompt()))
    for _ in range(n_qa):
        rows.append(row("knowledge_qa", qa_prompt()))
    return rows


def dedup(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for r in rows:
        k = (r["prompt"][:400], r["chosen"][:400])  # prompt+chosen unik
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def split(rows: List[Dict[str, Any]], ratios=(0.8, 0.1, 0.1)):
    random.shuffle(rows)
    n = len(rows)
    n_tr = int(n * ratios[0])
    n_val = int(n * ratios[1])
    return rows[:n_tr], rows[n_tr : n_tr + n_val], rows[n_tr + n_val :]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--support", type=int, default=120)
    ap.add_argument("--meeting", type=int, default=90)
    ap.add_argument("--qa", type=int, default=90)
    args = ap.parse_args()

    rows = dedup(make_rows(args.support, args.meeting, args.qa))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    tr, va, te = split(rows)
    base = Path("data/dpo_v1/splits/sv_synth")
    base.mkdir(parents=True, exist_ok=True)
    for name, data in [("train", tr), ("val", va), ("test", te)]:
        with (base / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("✅ SV-syntet klart:", len(rows), "par")


if __name__ == "__main__":
    main()
