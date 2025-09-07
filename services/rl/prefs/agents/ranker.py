#!/usr/bin/env python3
# Borda-aggregation av domar: input: [{"prompt":..., "candidates":[{"id":"A","score":..}, ...]}]
def borda_rank(candidates):
    # candidates: list of (id, score) högre= bättre
    sorted_c = sorted(candidates, key=lambda x: x["score"], reverse=True)
    n=len(sorted_c)
    return {c["id"]: (n-i-1) for i,c in enumerate(sorted_c)}