#!/usr/bin/env python3
from typing import Any, Dict

from .aggregator import bradley_terry
from .pairwise import Triple
from .ranker import borda_rank


def judge(triple: Triple, mode: str = "borda+bt") -> Dict[str, Any]:
    """
    mode:
      - "borda+bt": Borda poäng för ranking -> BT för parvis fit
      - "borda-only": Borda och välj högsta poäng direkt
    Returnerar {"winner_id": "...", "scores": {...}, "mode": mode}
    """
    # 1) Borda-score från "observations" (här proxar vi med textlängd/heuristik)
    #    OBS: I verklig drift bör denna komma från preferenssignal/heuristik.
    candidates = [
        {"id": c.id, "score": _heuristic_score(c.text)} for c in triple.candidates
    ]
    borda_scores = borda_rank(candidates)  # id -> poäng (0..n-1)

    if mode == "borda-only":
        winner = max(borda_scores.items(), key=lambda kv: kv[1])[0]
        return {"winner_id": winner, "scores": {"borda": borda_scores}, "mode": mode}

    # 2) Borda -> generera par för BT, vikta implicit med bordaordning
    #    Här simulerar vi par där "högre borda" antas vinna
    ids_sorted = [
        k for k, _ in sorted(borda_scores.items(), key=lambda kv: kv[1], reverse=True)
    ]
    pairs = []
    for i in range(len(ids_sorted)):
        for j in range(i + 1, len(ids_sorted)):
            pairs.append({"winner": ids_sorted[i], "loser": ids_sorted[j]})
    skills = bradley_terry(pairs, iters=30, lr=0.2)
    # välj med högst "skill"
    winner = max(skills.items(), key=lambda kv: kv[1])[0] if skills else ids_sorted[0]
    return {
        "winner_id": winner,
        "scores": {"borda": borda_scores, "bt": skills},
        "mode": mode,
    }


def _heuristic_score(text: str) -> float:
    # Enkel heuristik för demo: kort+konkret ger lite bonus.
    L = len(text or "")
    bonus = 0.5 if L < 280 else 0.0
    return max(0.0, 1.0 - (L / 1000.0)) + bonus
