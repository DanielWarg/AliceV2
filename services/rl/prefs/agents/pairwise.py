#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Candidate:
    id: str
    text: str
    score: float | None = None  # optional "true" score for simulation


@dataclass
class Triple:
    prompt: str
    candidates: List[Candidate]  # exactly 3
    winner_id: str | None = None  # ground-truth for eval (optional)


def to_pairwise(triple: Triple) -> List[Dict[str, str]]:
    """Expand a triple into pairwise duels for Bradley–Terry style fits."""
    ids = [c.id for c in triple.candidates]
    pairs = []
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = ids[i], ids[j]
            # If we know ground-truth winner, label accordingly; else unlabeled
            if triple.winner_id in (a, b):
                w = triple.winner_id
                loser = b if w == a else a
                pairs.append({"winner": w, "loser": loser})
            else:
                pairs.append({"winner": a, "loser": b})  # arbitrary if unknown
    return pairs
